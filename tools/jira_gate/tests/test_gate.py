import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gate


REPOSITORY = "sagarsalunkhe2025/Hackathon"
SHA = "a" * 40
OTHER_SHA = "b" * 40


def make_pr(
    *,
    title="DEMO-101: synthetic example",
    body=None,
    sha=SHA,
    state="open",
    base=gate.TARGET_BRANCH,
    base_repo=REPOSITORY,
    head_repo=REPOSITORY,
):
    return {
        "number": 7,
        "state": state,
        "title": title,
        "body": body,
        "base": {"ref": base, "repo": {"full_name": base_repo}},
        "head": {
            "sha": sha,
            "repo": {"full_name": head_repo} if head_repo else None,
        },
    }


def make_event(event_name="pull_request_target", action="opened", pr_number=7):
    event = {"repository": {"full_name": REPOSITORY, "default_branch": "main"}}
    if event_name == "pull_request_target":
        event.update({"action": action, "pull_request": {"number": pr_number}})
    else:
        event["inputs"] = {"pr_number": str(pr_number)}
    return event


class FakeGitHub:
    def __init__(self, *pulls, default_branch="main"):
        self.pulls = list(pulls)
        self.default_branch = default_branch
        self.statuses = []

    def get_repository(self):
        return {"default_branch": self.default_branch}

    def get_pull_request(self, number):
        self.asserted_number = number
        if len(self.pulls) > 1:
            return self.pulls.pop(0)
        return self.pulls[0]

    def create_status(self, sha, state, description):
        self.statuses.append((sha, state, gate.status_payload(state, description)))


class FakeJira(gate.JiraClient):
    def __init__(self, issues):
        self.issues = issues
        self.lookups = []

    def get_issue(self, ticket):
        self.lookups.append(ticket)
        issue = self.issues[ticket]
        if isinstance(issue, Exception):
            raise issue
        return issue


class TitleParserTests(unittest.TestCase):
    def test_parses_deduplicated_tickets(self):
        self.assertEqual(
            gate.parse_title_tickets(
                "[demo-101] fixes DEMO-102 and DEMO-101", "DEMO"
            ),
            ["DEMO-101", "DEMO-102"],
        )

    def test_requires_title_ticket_and_rejects_wrong_or_malformed_keys(self):
        for title in (
            "No ticket here",
            "DEMO-0",
            "DEMO-",
            "DEMO-ABC",
            "OTHER-12",
            "DEMO-1234567890",
        ):
            with self.subTest(title=title), self.assertRaises(gate.GateFailure):
                gate.parse_title_tickets(title, "DEMO")

    def test_rejects_empty_or_overlong_title_and_too_many_tickets(self):
        for title in (None, "", "x" * (gate.MAX_TITLE_LENGTH + 1)):
            with self.subTest(title=title), self.assertRaises(gate.GateFailure):
                gate.parse_title_tickets(title, "DEMO")
        title = " ".join(f"DEMO-{number}" for number in range(1, 12))
        with self.assertRaises(gate.GateFailure):
            gate.parse_title_tickets(title, "DEMO")

    def test_prefix_is_configurable(self):
        self.assertEqual(gate.parse_title_tickets("ABC-123", "ABC"), ["ABC-123"])

    def test_hyphenated_prose_is_not_treated_as_a_ticket(self):
        self.assertEqual(
            gate.parse_title_tickets("DEMO-101: non-functional change", "DEMO"),
            ["DEMO-101"],
        )


class DescriptionParserTests(unittest.TestCase):
    def test_description_only_plain_bracketed_and_linked_keys(self):
        for entry in (
            "DEMO-101 Synthetic change",
            "[DEMO-101] Synthetic change",
            "[DEMO-101](https://example.atlassian.net/browse/DEMO-101) Synthetic change",
            '<a href="https://example.atlassian.net/browse/DEMO-101">DEMO-101</a> Synthetic change',
        ):
            with self.subTest(entry=entry):
                self.assertEqual(
                    gate.parse_pr_tickets("Synthetic change", "## Jira tickets\n" + entry, "DEMO"),
                    ["DEMO-101"],
                )

    def test_combines_sources_and_all_sections_in_first_seen_order(self):
        self.assertEqual(
            gate.parse_pr_tickets(
                "DEMO-101 Synthetic change",
                "## JIRA TICKETS\n[demo-101] DEMO-102\n"
                "## Notes\nDEMO-999\n## Jira tickets ##\nDEMO-103",
                "DEMO",
            ),
            ["DEMO-101", "DEMO-102", "DEMO-103"],
        )

    def test_null_missing_and_empty_bodies_allow_title_only(self):
        for body in (None, ""):
            self.assertEqual(gate.parse_pr_tickets("DEMO-101", body, "DEMO"), ["DEMO-101"])
        pr = make_pr()
        del pr["body"]
        self.assertEqual(gate.validate_pr_structure(pr, REPOSITORY, gate.GateConfig()), ["DEMO-101"])

    def test_requires_a_key_in_authoritative_sources(self):
        for body in (
            None, "", "DEMO-101", "## Notes\nDEMO-101", "### Jira tickets\nDEMO-101",
            "## Jira tickets\n\n## Notes\nDEMO-101",
            "```\n## Jira tickets\nDEMO-101\n```",
        ):
            with self.subTest(body=body), self.assertRaisesRegex(gate.GateFailure, "missing_ticket"):
                gate.parse_pr_tickets("Synthetic change", body, "DEMO")

    def test_markdown_heading_boundaries(self):
        for boundary in ("## Notes", "# Notes", "Notes\n=====", "Notes\n-----"):
            with self.subTest(boundary=boundary):
                self.assertEqual(
                    gate.parse_pr_tickets(
                        "Synthetic change",
                        "## Jira tickets\nDEMO-101\n### Details DEMO-102\n"
                        + boundary + "\nOTHER-999",
                        "DEMO",
                    ),
                    ["DEMO-101", "DEMO-102"],
                )
        self.assertEqual(
            gate.parse_pr_tickets(
                "Synthetic change",
                "## Jira tickets\nDEMO-101\n```\n## Notes\n```\nDEMO-102",
                "DEMO",
            ),
            ["DEMO-101", "DEMO-102"],
        )

    def test_horizontal_rule_after_list_item_does_not_hide_tickets(self):
        for entry in ("- DEMO-102", "* DEMO-102", "+ DEMO-102", "1. DEMO-102", "1) DEMO-102"):
            body = f"## Jira tickets\nDEMO-101\n\n{entry}\n---\nDEMO-103"
            with self.subTest(entry=entry):
                self.assertEqual(
                    gate.parse_pr_tickets("Synthetic change", body, "DEMO"),
                    ["DEMO-101", "DEMO-102", "DEMO-103"],
                )
                pr = make_pr(title="Synthetic change", body=body)
                with self.assertRaisesRegex(gate.GateFailure, "jira_validation_failed"):
                    gate.run_validation(
                        REPOSITORY, "pull_request_target", make_event(), "refs/heads/main",
                        FakeGitHub(pr, pr), gate.MockJiraClient(), gate.GateConfig(),
                    )

    def test_malformed_or_wrong_prefix_cannot_be_hidden_by_fallback(self):
        for key in ("DEMO-0", "DEMO-", "DEMO-ABC", "DEMO-1234567890", "OTHER-12"):
            for title, body in (
                (key, "## Jira tickets\nDEMO-101"),
                ("DEMO-101", "## Jira tickets\n" + key),
            ):
                with self.subTest(title=title, body=body), self.assertRaisesRegex(
                    gate.GateFailure, "invalid_ticket_key"
                ):
                    gate.parse_pr_tickets(title, body, "DEMO")

    def test_conflicting_link_keys_are_both_validated(self):
        for entry in (
            "[DEMO-101](https://example.atlassian.net/browse/DEMO-102)",
            '<a href="https://example.atlassian.net/browse/DEMO-102">DEMO-101</a>',
            "[DEMO-101](https://example.atlassian.net/browse/DEMO%2D102)",
            '<a href="https://example.atlassian.net/browse/DEMO&#45;102">DEMO-101</a>',
        ):
            with self.subTest(entry=entry):
                self.assertEqual(
                    set(gate.parse_pr_tickets("Synthetic change", "## Jira tickets\n" + entry, "DEMO")),
                    {"DEMO-101", "DEMO-102"},
                )
        with self.assertRaisesRegex(gate.GateFailure, "invalid_ticket_key"):
            gate.parse_pr_tickets(
                "DEMO-101", "## Jira tickets\n[DEMO-101](https://example.test/OTHER-12)", "DEMO"
            )

    def test_reference_links_fail_closed_without_hiding_external_destinations(self):
        for entry, definition in (
            ("[DEMO-101][ticket]", "[ticket]: https://example.test/OTHER-12"),
            ("[DEMO-101][]", "[DEMO-101]: https://example.test/DEMO-102"),
            ("[DEMO-101]", "[demo-101]: https://example.test/DEMO-102"),
        ):
            with self.subTest(entry=entry), self.assertRaisesRegex(
                gate.GateFailure, "unsupported_reference_link"
            ):
                gate.parse_pr_tickets(
                    "Synthetic change",
                    f"## Jira tickets\n{entry}\n## Notes\n{definition}",
                    "DEMO",
                )
        self.assertEqual(
            gate.parse_pr_tickets(
                "Synthetic change",
                "## Jira tickets\n[DEMO-101]\n## Notes\n"
                "[unrelated]: https://example.test/OTHER-12",
                "DEMO",
            ),
            ["DEMO-101"],
        )
        self.assertEqual(
            gate.parse_pr_tickets("Synthetic change", "## Jira tickets\n[DEMO-101] [DEMO-102]", "DEMO"),
            ["DEMO-101", "DEMO-102"],
        )

    def test_body_and_combined_ticket_limits(self):
        for body in (42, [], "x" * (gate.MAX_BODY_LENGTH + 1)):
            with self.subTest(body_type=type(body)), self.assertRaisesRegex(
                gate.GateFailure, "invalid_body"
            ):
                gate.parse_pr_tickets("DEMO-101", body, "DEMO")
        self.assertEqual(
            gate.parse_pr_tickets("DEMO-101", "x" * gate.MAX_BODY_LENGTH, "DEMO"),
            ["DEMO-101"],
        )
        for title_count in (0, 5):
            with self.subTest(title_count=title_count), self.assertRaisesRegex(
                gate.GateFailure, "too_many_tickets"
            ):
                gate.parse_pr_tickets(
                    "Synthetic change " + " ".join(f"DEMO-{i}" for i in range(1, title_count + 1)),
                    "## Jira tickets\n" + " ".join(f"DEMO-{i}" for i in range(title_count + 1, 12)),
                    "DEMO",
                )


class JiraFieldTests(unittest.TestCase):
    def test_reads_only_exact_custom_field_option_value(self):
        issue = {
            "fields": {
                "customfield_12490": {"value": "2026.4.0", "id": "option-ignored"},
                "customfield_12621": {"value": "wrong"},
                "fixVersions": [{"name": "wrong"}],
            }
        }
        gate.validate_issue(issue, "customfield_12490", "2026.4.0")

    def test_mismatch_absent_and_malformed_fields_block(self):
        cases = (
            {"fields": {"customfield_12490": {"value": "2026.3.1"}}},
            {"fields": {"customfield_12490": None}},
            {"fields": {"customfield_12490": {"id": "option-without-value"}}},
            {"fields": {"customfield_12490": {"value": ""}}},
            {"fields": {"customfield_12490": {"value": " 2026.4.0"}}},
            {"fields": {}},
            {},
        )
        for issue in cases:
            with self.subTest(issue=issue), self.assertRaises(gate.GateFailure):
                gate.validate_issue(issue, "customfield_12490", "2026.4.0")


class ConfigurationAndMockTests(unittest.TestCase):
    def test_live_client_selection_does_not_use_mock_or_connect(self):
        with patch.object(gate, "LiveJiraClient") as live, patch.object(gate, "MockJiraClient") as mock:
            config = gate.GateConfig(mode="live")
            self.assertIs(gate.create_jira_client(config), live.return_value)
            live.assert_called_once_with(config)
            mock.assert_not_called()

    def test_mock_mode_uses_only_synthetic_fixtures(self):
        client = gate.create_jira_client(gate.GateConfig())
        self.assertIsInstance(client, gate.MockJiraClient)
        gate.validate_issue(client.get_issue("DEMO-101"), "customfield_12490", "2026.4.0")
        for ticket in ("DEMO-102", "DEMO-103", "DEMO-404", "DEMO-500"):
            with self.subTest(ticket=ticket):
                if ticket in {"DEMO-404", "DEMO-500"}:
                    with self.assertRaises(gate.JiraLookupFailure):
                        client.get_issue(ticket)
                else:
                    with self.assertRaises(gate.GateFailure):
                        gate.validate_issue(
                            client.get_issue(ticket), "customfield_12490", "2026.4.0"
                        )

    def test_invalid_modes_field_ids_and_live_hosts_are_rejected(self):
        for config in (
            gate.GateConfig(mode="unknown"),
            gate.GateConfig(field_id="Target Version"),
            gate.GateConfig(
                mode="live",
                jira_base_url="http://jira.example.test",
                jira_allowed_host="jira.example.test",
                jira_email="user",
                jira_api_token="token",
            ),
            gate.GateConfig(
                mode="live",
                jira_base_url="https://other.example.test",
                jira_allowed_host="jira.example.test",
                jira_email="user",
                jira_api_token="token",
            ),
            gate.GateConfig(
                mode="live",
                jira_base_url="https://user@jira.example.test",
                jira_allowed_host="jira.example.test",
                jira_email="user",
                jira_api_token="token",
            ),
        ):
            with self.subTest(config=config), self.assertRaises(gate.GateFailure):
                config.validate()

    def test_live_client_uses_bounded_https_get_and_no_redirects(self):
        seen = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def geturl(self):
                return "https://jira.example.test/rest/api/3/issue/DEMO-101?fields=customfield_12490"

            def read(self, limit):
                seen["read_limit"] = limit
                return b'{"fields":{"customfield_12490":{"value":"2026.4.0"}}}'

        class FakeOpener:
            def open(self, request, timeout):
                seen["request"] = request
                seen["timeout"] = timeout
                return FakeResponse()

        config = gate.GateConfig(
            mode="live",
            jira_base_url="https://jira.example.test",
            jira_allowed_host="jira.example.test",
            jira_email="demo@example.test",
            jira_api_token="synthetic-token",
        )
        client = gate.LiveJiraClient(config, FakeOpener())
        issue = client.get_issue("DEMO-101")
        self.assertEqual(issue["fields"]["customfield_12490"]["value"], "2026.4.0")
        self.assertEqual(seen["timeout"], gate.HTTP_TIMEOUT_SECONDS)
        self.assertEqual(seen["read_limit"], gate.MAX_RESPONSE_BYTES + 1)
        self.assertEqual(seen["request"].get_method(), "GET")
        self.assertNotIn("synthetic-token", seen["request"].full_url)
        handler = gate._NoRedirectHandler()
        self.assertIsNone(
            handler.redirect_request(
                seen["request"], None, 302, "redirect", {}, "https://other.example.test"
            )
        )


class PullRequestValidationTests(unittest.TestCase):
    def test_description_only_and_duplicate_keys_use_mock_client(self):
        pr = make_pr(
            title="Synthetic change",
            body="## Jira tickets\n[DEMO-101](https://untrusted.example.test/DEMO-101)",
        )
        jira = gate.MockJiraClient()
        with patch.object(jira, "get_issue", wraps=jira.get_issue) as lookup:
            result = gate.run_validation(
                REPOSITORY, "pull_request_target", make_event(action="edited"),
                "refs/heads/main", FakeGitHub(pr, pr), jira, gate.GateConfig(),
            )
        self.assertEqual(result["tickets_validated"], 1)
        lookup.assert_called_once_with("DEMO-101")

    def test_body_cannot_override_mismatching_title_or_link_destination(self):
        for title, body in (
            ("DEMO-102", "## Jira tickets\nDEMO-101"),
            ("DEMO-101", "## Jira tickets\nDEMO-102"),
            ("Synthetic change", "## Jira tickets\nDEMO-101 DEMO-102 DEMO-103"),
            ("Synthetic change", "## Jira tickets\n[DEMO-101](https://example.test/DEMO-102)"),
        ):
            pr = make_pr(title=title, body=body)
            with self.subTest(title=title, body=body), self.assertRaisesRegex(
                gate.GateFailure, "jira_validation_failed"
            ):
                gate.run_validation(
                    REPOSITORY, "pull_request_target", make_event(), "refs/heads/main",
                    FakeGitHub(pr, pr), gate.MockJiraClient(), gate.GateConfig(),
                )

    def test_body_change_between_pending_initial_and_final_reads_blocks(self):
        initial = make_pr(body="## Jira tickets\nDEMO-101")
        changed = make_pr(body="## Jira tickets\nDEMO-102")
        for pulls, expected_lookups in (((changed,), []), ((initial, changed), ["DEMO-101"])):
            jira = FakeJira(
                {"DEMO-101": {"fields": {"customfield_12490": {"value": "2026.4.0"}}}}
            )
            with self.subTest(reads=len(pulls)), self.assertRaisesRegex(
                gate.GateFailure, "pull_request_changed"
            ):
                gate.run_validation(
                    REPOSITORY, "pull_request_target", make_event(), "refs/heads/main",
                    FakeGitHub(*pulls), jira, gate.GateConfig(),
                    expected_snapshot=json.dumps(gate.snapshot_pr(initial)),
                )
            self.assertEqual(jira.lookups, expected_lookups)

    def test_workflow_and_python_snapshots_have_identical_order_and_normalization(self):
        workflow = Path(__file__).resolve().parents[3] / ".github/workflows/jira-target-version.yml"
        source = workflow.read_text(encoding="utf-8")
        snapshot_js = source.split("const snapshot = ", 1)[1].split(";", 1)[0]
        for body in (None, "", "## Jira tickets\n[DEMO-101] Synthetic change\né"):
            pr = make_pr(body=body)
            for missing in (False, True):
                pull = dict(pr)
                if missing:
                    del pull["body"]
                result = subprocess.run(
                    ["node", "-e",
                     "const pull = JSON.parse(process.argv[1]);"
                     f"console.log(JSON.stringify({snapshot_js}));",
                     json.dumps(pull)],
                    check=True, capture_output=True, text=True,
                )
                self.assertEqual(json.loads(result.stdout), list(gate.snapshot_pr(pull)))
                gate._validate_expected_snapshot(pull, result.stdout)

    def test_requires_expected_repository_destination_and_open_pr(self):
        for pr in (
            make_pr(base="main"),
            make_pr(state="closed"),
            make_pr(base_repo="another/repository"),
        ):
            with self.subTest(pr=pr), self.assertRaises(gate.GateFailure):
                gate.validate_pr_structure(pr, REPOSITORY, gate.GateConfig())

    def test_live_mode_rejects_public_fork_pr(self):
        config = gate.GateConfig(mode="live")
        with self.assertRaises(gate.GateFailure):
            gate.validate_pr_structure(
                make_pr(head_repo="forker/Hackathon"), REPOSITORY, config
            )

    def test_all_title_tickets_must_match(self):
        pr = make_pr(title="demo-101 and DEMO-102")
        github = FakeGitHub(pr, pr)
        jira = FakeJira(
            {
                "DEMO-101": {"fields": {"customfield_12490": {"value": "2026.4.0"}}},
                "DEMO-102": {"fields": {"customfield_12490": {"value": "2026.3.1"}}},
            }
        )
        with self.assertRaises(gate.GateFailure):
            gate.run_validation(
                REPOSITORY,
                "pull_request_target",
                make_event(),
                "refs/heads/main",
                github,
                jira,
                gate.GateConfig(),
            )
        self.assertEqual(jira.lookups, ["DEMO-101", "DEMO-102"])

    def test_metadata_change_during_validation_blocks_result(self):
        github = FakeGitHub(make_pr(), make_pr(sha=OTHER_SHA))
        jira = FakeJira(
            {"DEMO-101": {"fields": {"customfield_12490": {"value": "2026.4.0"}}}}
        )
        with self.assertRaises(gate.GateFailure):
            gate.run_validation(
                REPOSITORY,
                "pull_request_target",
                make_event(),
                "refs/heads/main",
                github,
                jira,
                gate.GateConfig(),
            )

    def test_manual_event_requires_default_branch_and_fetches_current_pr(self):
        event = make_event("workflow_dispatch")
        jira = FakeJira(
            {"DEMO-101": {"fields": {"customfield_12490": {"value": "2026.4.0"}}}}
        )
        with self.assertRaises(gate.GateFailure):
            gate.run_validation(
                REPOSITORY,
                "workflow_dispatch",
                event,
                "refs/heads/untrusted",
                FakeGitHub(make_pr()),
                jira,
                gate.GateConfig(),
            )
        self.assertEqual(jira.lookups, [])
        invalid_number_event = make_event("workflow_dispatch")
        invalid_number_event["inputs"]["pr_number"] = 7.5
        with self.assertRaises(gate.GateFailure):
            gate.run_validation(
                REPOSITORY,
                "workflow_dispatch",
                invalid_number_event,
                "refs/heads/main",
                FakeGitHub(make_pr()),
                jira,
                gate.GateConfig(),
            )
        self.assertEqual(jira.lookups, [])
        result = gate.run_validation(
            REPOSITORY,
            "workflow_dispatch",
            event,
            "refs/heads/main",
            FakeGitHub(make_pr(), make_pr()),
            jira,
            gate.GateConfig(),
        )
        self.assertEqual(result["head_sha"], SHA)

    def test_automatic_event_rejects_other_actions_and_repository(self):
        github = FakeGitHub(make_pr(), make_pr())
        jira = FakeJira({})
        with self.assertRaises(gate.GateFailure):
            gate.run_validation(
                REPOSITORY,
                "pull_request_target",
                make_event(action="closed"),
                "refs/heads/main",
                github,
                jira,
                gate.GateConfig(),
            )
        with self.assertRaises(gate.GateFailure):
            gate.run_validation(
                "someone/else",
                "pull_request_target",
                make_event(),
                "refs/heads/main",
                github,
                jira,
                gate.GateConfig(),
            )

    def test_pending_snapshot_is_verified_before_jira_lookup(self):
        pr = make_pr()
        changed = make_pr(title="DEMO-102: edited during startup")
        jira = FakeJira({})
        with self.assertRaises(gate.GateFailure):
            gate.run_validation(
                REPOSITORY,
                "pull_request_target",
                make_event(),
                "refs/heads/main",
                FakeGitHub(changed),
                jira,
                gate.GateConfig(),
                expected_snapshot=json.dumps(gate.snapshot_pr(pr)),
            )
        self.assertEqual(jira.lookups, [])


class StatusTests(unittest.TestCase):
    def run_environment_gate(self, issue, pulls):
        github = FakeGitHub(*pulls)
        jira = FakeJira({"DEMO-101": issue})
        with tempfile.TemporaryDirectory() as temp_dir:
            event_path = Path(temp_dir) / "event.json"
            event_path.write_text(
                json.dumps(make_event()), encoding="utf-8"
            )
            env = {
                "GITHUB_REPOSITORY": REPOSITORY,
                "GITHUB_TOKEN": "test-token",
                "GITHUB_REF": "refs/heads/main",
                "GITHUB_EVENT_NAME": "pull_request_target",
                "GITHUB_EVENT_PATH": str(event_path),
                "JIRA_GATE_MODE": "mock",
            }
            with patch.object(gate, "GitHubApi", return_value=github), patch.object(
                gate, "create_jira_client", return_value=jira
            ), contextlib.redirect_stdout(io.StringIO()):
                result = gate.run_from_environment(env)
        return result, github.statuses

    def test_mock_success_publishes_status_on_fresh_pr_head(self):
        issue = {"fields": {"customfield_12490": {"value": "2026.4.0"}}}
        result, statuses = self.run_environment_gate(issue, [make_pr(), make_pr()])
        self.assertEqual(result, 0)
        self.assertEqual(len(statuses), 1)
        sha, state, payload = statuses[0]
        self.assertEqual(sha, SHA)
        self.assertEqual(state, "success")
        self.assertEqual(payload["context"], "jira-target-version")
        self.assertTrue(payload["description"].startswith("MOCK:"))

    def test_mismatch_publishes_failure_without_ticket_details(self):
        issue = {"fields": {"customfield_12490": {"value": "2026.3.1"}}}
        result, statuses = self.run_environment_gate(issue, [make_pr(), make_pr()])
        self.assertEqual(result, 1)
        self.assertEqual(len(statuses), 1)
        sha, state, payload = statuses[0]
        self.assertEqual((sha, state), (SHA, "failure"))
        self.assertEqual(payload["context"], "jira-target-version")
        self.assertNotIn("DEMO-101", payload["description"])

    def test_status_payload_uses_exact_context_and_current_head_path(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def read(self, _):
                return b"{}"

        calls = []

        def opener(request, timeout):
            calls.append((request, timeout))
            return Response()

        client = gate.GitHubApi(REPOSITORY, "test-token", opener)
        client.create_status(SHA, "success", "synthetic pass")
        request, timeout = calls[0]
        self.assertEqual(
            request.full_url,
            f"https://api.github.com/repos/{REPOSITORY}/statuses/{SHA}",
        )
        self.assertEqual(json.loads(request.data)["context"], "jira-target-version")
        self.assertEqual(json.loads(request.data)["state"], "success")
        self.assertEqual(gate.STATUS_CONTEXT, "jira-target-version")
        self.assertEqual(timeout, gate.HTTP_TIMEOUT_SECONDS)
        self.assertEqual(request.get_header("Authorization"), "Bearer " + "test-token")

    def test_status_descriptions_mark_mock_results(self):
        self.assertTrue(gate._status_description(gate.GateConfig(), True).startswith("MOCK:"))
        self.assertFalse(gate._status_description(gate.GateConfig(mode="live"), True).startswith("MOCK:"))


if __name__ == "__main__":
    unittest.main()
