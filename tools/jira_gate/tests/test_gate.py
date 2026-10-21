import contextlib
import io
import json
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
