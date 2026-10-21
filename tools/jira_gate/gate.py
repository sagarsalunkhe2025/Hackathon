#!/usr/bin/env python3
"""Standalone Jira target-version gate for the synthetic test destination."""

from __future__ import annotations

import base64
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


EXPECTED_REPOSITORY = "sagarsalunkhe2025/Hackathon"
TARGET_BRANCH = "test-jira-gate-2026.4.0"
DEFAULT_VERSION = "2026.4.0"
DEFAULT_FIELD_ID = "customfield_12490"
DEFAULT_TICKET_PREFIX = "DEMO"
STATUS_CONTEXT = "jira-target-version"
MAX_TITLE_LENGTH = 512
MAX_BODY_LENGTH = 65_536
MAX_TICKETS = 10
MAX_RESPONSE_BYTES = 65_536
HTTP_TIMEOUT_SECONDS = 10
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
GENERIC_TICKET_RE = re.compile(
    r"(?<![A-Za-z0-9-])([A-Z][A-Z0-9]{0,9}-[0-9][A-Z0-9-]*)(?![A-Za-z0-9-])",
    re.IGNORECASE,
)


class GateFailure(Exception):
    """A safe-to-report validation failure."""


class JiraLookupFailure(Exception):
    """A Jira lookup failed without exposing response details."""


@dataclass(frozen=True)
class GateConfig:
    mode: str = "mock"
    target_version: str = DEFAULT_VERSION
    field_id: str = DEFAULT_FIELD_ID
    ticket_prefix: str = DEFAULT_TICKET_PREFIX
    jira_base_url: str = ""
    jira_allowed_host: str = ""
    jira_email: str = ""
    jira_api_token: str = ""

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "GateConfig":
        config = cls(
            mode=env.get("JIRA_GATE_MODE", "mock").strip().lower(),
            target_version=env.get("JIRA_GATE_VERSION", DEFAULT_VERSION),
            field_id=env.get("JIRA_FIELD_ID", DEFAULT_FIELD_ID),
            ticket_prefix=env.get("JIRA_TICKET_PREFIX", DEFAULT_TICKET_PREFIX).upper(),
            jira_base_url=env.get("JIRA_BASE_URL", ""),
            jira_allowed_host=env.get("JIRA_ALLOWED_HOST", "").lower(),
            jira_email=env.get("JIRA_EMAIL", ""),
            jira_api_token=env.get("JIRA_API_TOKEN", ""),
        )
        config.validate()
        return config

    def validate(self) -> None:
        if self.mode not in {"mock", "live"}:
            raise GateFailure("invalid_mode")
        if not re.fullmatch(r"customfield_[0-9]+", self.field_id):
            raise GateFailure("invalid_field_configuration")
        if not re.fullmatch(r"[A-Z][A-Z0-9]{0,9}", self.ticket_prefix):
            raise GateFailure("invalid_prefix_configuration")
        if not self.target_version or self.target_version != self.target_version.strip():
            raise GateFailure("invalid_version_configuration")
        if self.mode == "live":
            validate_jira_url(self.jira_base_url, self.jira_allowed_host)
            if not self.jira_email or not self.jira_api_token:
                raise GateFailure("missing_jira_credentials")


def validate_jira_url(base_url: str, allowed_host: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(base_url)
        port = parsed.port
    except ValueError as exc:
        raise GateFailure("invalid_jira_url") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or port not in {None, 443}
        or not allowed_host
        or parsed.hostname.lower() != allowed_host
    ):
        raise GateFailure("invalid_jira_url")
    return f"https://{parsed.hostname.lower()}"


def parse_title_tickets(title: Any, prefix: str) -> list[str]:
    if not isinstance(title, str) or not title or len(title) > MAX_TITLE_LENGTH:
        raise GateFailure("invalid_title")
    tickets = _parse_ticket_keys(title, prefix)
    if not tickets:
        raise GateFailure("missing_ticket")
    return tickets


def _parse_ticket_keys(text: str, prefix: str) -> list[str]:
    expected_prefix = prefix.upper()
    tickets: list[str] = []
    seen: set[str] = set()
    configured_ticket_re = re.compile(
        rf"(?<![A-Za-z0-9-])({re.escape(expected_prefix)}-[A-Z0-9-]*)(?![A-Za-z0-9-])",
        re.IGNORECASE,
    )
    candidates = [
        (match.start(), match.group(1).upper())
        for pattern in (configured_ticket_re, GENERIC_TICKET_RE)
        for match in pattern.finditer(text)
    ]
    for _, candidate in sorted(candidates):
        valid = re.fullmatch(
            rf"{re.escape(expected_prefix)}-[1-9][0-9]{{0,8}}",
            candidate,
        )
        if not valid:
            raise GateFailure("invalid_ticket_key")
        if candidate not in seen:
            seen.add(candidate)
            tickets.append(candidate)
            if len(tickets) > MAX_TICKETS:
                raise GateFailure("too_many_tickets")
    return tickets


def jira_sections(body: Any) -> str:
    if body is None:
        return ""
    if not isinstance(body, str) or len(body) > MAX_BODY_LENGTH:
        raise GateFailure("invalid_body")
    lines = body.splitlines()
    selected: list[str] = []
    active = False
    fence = ""
    for index, line in enumerate(lines):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            run = marker.group(1)
            if not fence:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence) and not line[marker.end():].strip():
                fence = ""
            continue
        if not fence:
            heading = re.match(r"^ {0,3}(#{1,6})(?:[ \t]+(.*)|[ \t]*)$", line)
            if heading:
                level = len(heading.group(1))
                label = re.sub(r"[ \t]+#+[ \t]*$", "", heading.group(2) or "").strip()
                if level <= 2:
                    active = level == 2 and label.casefold() == "jira tickets"
                    continue
            if (
                line.strip()
                and heading is None
                and not re.match(
                    r"^(?: {4}|\t)|^ {0,3}(?:>|[-+*](?:[ \t]|$)|"
                    r"[0-9]{1,9}[.)](?:[ \t]|$)|(?:[-*_][ \t]*){3,}$)",
                    line,
                )
                and index + 1 < len(lines)
                and re.fullmatch(r" {0,3}(?:=+|-+)[ \t]*", lines[index + 1])
            ):
                active = False
        if active:
            selected.append(line)
    return "\n".join(selected)


def parse_pr_tickets(title: Any, body: Any, prefix: str) -> list[str]:
    if not isinstance(title, str) or not title or len(title) > MAX_TITLE_LENGTH:
        raise GateFailure("invalid_title")
    title_tickets = _parse_ticket_keys(title, prefix)
    section = jira_sections(body)
    reference_labels = {
        " ".join(label.split()).casefold()
        for label in re.findall(r"(?m)^ {0,3}\[([^\]\n]+)\]:", body or "")
    }
    if any(
        " ".join(label.split()).casefold() in reference_labels
        for label in re.findall(r"\[([^\]\n]+)\]", section)
    ):
        raise GateFailure("unsupported_reference_link")
    # Validate keys in both link labels and destinations, never fetch body URLs.
    section = urllib.parse.unquote(html.unescape(section))
    body_tickets = _parse_ticket_keys(section, prefix)
    tickets = list(dict.fromkeys(title_tickets + body_tickets))
    if len(tickets) > MAX_TICKETS:
        raise GateFailure("too_many_tickets")
    if not tickets:
        raise GateFailure("missing_ticket")
    return tickets


def extract_option_value(issue: Any, field_id: str) -> str:
    if not isinstance(issue, Mapping):
        raise GateFailure("malformed_issue")
    fields = issue.get("fields")
    if not isinstance(fields, Mapping):
        raise GateFailure("missing_target_field")
    option = fields.get(field_id)
    if not isinstance(option, Mapping):
        raise GateFailure("missing_target_field")
    value = option.get("value")
    if not isinstance(value, str) or not value or value != value.strip():
        raise GateFailure("malformed_target_field")
    return value


def validate_issue(issue: Any, field_id: str, expected_version: str) -> None:
    if extract_option_value(issue, field_id) != expected_version:
        raise GateFailure("target_version_mismatch")


def snapshot_pr(pr: Mapping[str, Any]) -> tuple[Any, ...]:
    base = pr.get("base")
    head = pr.get("head")
    if not isinstance(base, Mapping) or not isinstance(head, Mapping):
        raise GateFailure("malformed_pull_request")
    base_repo = base.get("repo")
    head_repo = head.get("repo")
    if not isinstance(base_repo, Mapping):
        raise GateFailure("malformed_pull_request")
    return (
        pr.get("number"),
        pr.get("state"),
        pr.get("title"),
        head.get("sha"),
        base.get("ref"),
        base_repo.get("full_name"),
        head_repo.get("full_name") if isinstance(head_repo, Mapping) else None,
        pr.get("body") if pr.get("body") is not None else "",
    )


def validate_pr_structure(
    pr: Mapping[str, Any],
    repository: str,
    config: GateConfig,
) -> list[str]:
    if snapshot_pr(pr)[5] != repository:
        raise GateFailure("wrong_base_repository")
    if pr.get("state") != "open":
        raise GateFailure("pull_request_not_open")
    if pr.get("base", {}).get("ref") != TARGET_BRANCH:
        raise GateFailure("wrong_destination")
    sha = pr.get("head", {}).get("sha")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise GateFailure("invalid_head_sha")
    if config.mode == "live" and snapshot_pr(pr)[6] != repository:
        raise GateFailure("live_mode_fork_rejected")
    return parse_pr_tickets(pr.get("title"), pr.get("body"), config.ticket_prefix)


class GitHubApi:
    def __init__(self, repository: str, token: str, opener: Any = urllib.request.urlopen):
        self.repository = repository
        self.token = token
        self.opener = opener

    def request(self, method: str, path: str, body: Any = None) -> Any:
        if not self.token:
            raise GateFailure("missing_github_token")
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            f"https://api.github.com{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + self.token,
                "X-GitHub-Api-Version": "2022-11-28",
                **({"Content-Type": "application/json"} if data is not None else {}),
            },
        )
        try:
            with self.opener(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise GateFailure("github_response_too_large")
                return json.loads(raw)
        except GateFailure:
            raise
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise GateFailure("github_api_failure") from exc

    def get_repository(self) -> Mapping[str, Any]:
        result = self.request("GET", f"/repos/{self.repository}")
        if not isinstance(result, Mapping):
            raise GateFailure("malformed_repository")
        return result

    def get_pull_request(self, number: int) -> Mapping[str, Any]:
        result = self.request("GET", f"/repos/{self.repository}/pulls/{number}")
        if not isinstance(result, Mapping):
            raise GateFailure("malformed_pull_request")
        return result

    def create_status(self, sha: str, state: str, description: str) -> None:
        if not SHA_RE.fullmatch(sha) or state not in {"pending", "success", "failure"}:
            raise GateFailure("invalid_status")
        payload = status_payload(state, description)
        self.request(
            "POST",
            f"/repos/{self.repository}/statuses/{sha}",
            payload,
        )


def status_payload(state: str, description: str) -> dict[str, str]:
    return {
        "state": state,
        "context": STATUS_CONTEXT,
        "description": description[:140],
    }


class JiraClient:
    def get_issue(self, ticket: str) -> Any:
        raise NotImplementedError


class MockJiraClient(JiraClient):
    def __init__(self, fixture_path: Path | None = None):
        path = fixture_path or Path(__file__).with_name("fixtures") / "mock_issues.json"
        try:
            self.fixtures = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise JiraLookupFailure("mock_fixture_error") from exc

    def get_issue(self, ticket: str) -> Any:
        fixture = self.fixtures.get(ticket)
        if not isinstance(fixture, Mapping):
            raise JiraLookupFailure("mock_not_found")
        if fixture.get("error"):
            raise JiraLookupFailure("mock_lookup_error")
        return fixture


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


class LiveJiraClient(JiraClient):
    def __init__(self, config: GateConfig, opener: Any | None = None):
        self.base_url = validate_jira_url(config.jira_base_url, config.jira_allowed_host)
        credentials = f"{config.jira_email}:{config.jira_api_token}".encode("utf-8")
        self.authorization = "Basic " + base64.b64encode(credentials).decode("ascii")
        self.opener = opener or urllib.request.build_opener(_NoRedirectHandler())
        self.field_id = config.field_id

    def get_issue(self, ticket: str) -> Any:
        encoded_ticket = urllib.parse.quote(ticket, safe="")
        encoded_field = urllib.parse.quote(self.field_id, safe="")
        request = urllib.request.Request(
            f"{self.base_url}/rest/api/3/issue/{encoded_ticket}?fields={encoded_field}",
            headers={
                "Accept": "application/json",
                "Authorization": self.authorization,
            },
            method="GET",
        )
        try:
            with self.opener.open(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                if response.geturl() != request.full_url:
                    raise JiraLookupFailure("jira_redirect_rejected")
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise JiraLookupFailure("jira_response_too_large")
                return json.loads(raw)
        except JiraLookupFailure:
            raise
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            raise JiraLookupFailure("jira_api_failure") from exc


def create_jira_client(config: GateConfig) -> JiraClient:
    if config.mode == "mock":
        return MockJiraClient()
    return LiveJiraClient(config)


def _event_pr_number(event_name: str, event: Mapping[str, Any]) -> int:
    if event_name == "pull_request_target":
        action = event.get("action")
        if action not in {
            "opened",
            "synchronize",
            "reopened",
            "edited",
            "ready_for_review",
            "converted_to_draft",
        }:
            raise GateFailure("unsupported_pull_request_action")
        pull = event.get("pull_request")
        if not isinstance(pull, Mapping):
            raise GateFailure("missing_pull_request")
        number = pull.get("number")
    elif event_name == "workflow_dispatch":
        number = event.get("inputs", {}).get("pr_number")
    else:
        raise GateFailure("unsupported_event")
    if isinstance(number, bool):
        raise GateFailure("invalid_pull_request_number")
    if isinstance(number, int):
        parsed = number
    elif isinstance(number, str) and re.fullmatch(r"[0-9]{1,9}", number):
        parsed = int(number)
    else:
        raise GateFailure("invalid_pull_request_number")
    if parsed <= 0:
        raise GateFailure("invalid_pull_request_number")
    return parsed


def _verify_event_repository(event: Mapping[str, Any], repository: str) -> None:
    event_repository = event.get("repository")
    if not isinstance(event_repository, Mapping):
        raise GateFailure("missing_event_repository")
    full_name = event_repository.get("full_name")
    if not isinstance(full_name, str) or full_name.casefold() != repository.casefold():
        raise GateFailure("wrong_repository")
    if repository.casefold() != EXPECTED_REPOSITORY.casefold():
        raise GateFailure("wrong_repository")


def _check_manual_ref(
    event_name: str,
    ref: str,
    event: Mapping[str, Any],
    github: GitHubApi,
) -> None:
    if event_name != "workflow_dispatch":
        return
    repository = github.get_repository()
    default_branch = repository.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch:
        raise GateFailure("missing_default_branch")
    if ref != f"refs/heads/{default_branch}":
        raise GateFailure("manual_ref_not_default")
    event_default = event.get("repository", {}).get("default_branch")
    if event_default != default_branch:
        raise GateFailure("default_branch_changed")


def _validate_expected_snapshot(
    pr: Mapping[str, Any],
    expected_snapshot: str | None,
) -> tuple[Any, ...]:
    current = snapshot_pr(pr)
    if expected_snapshot:
        try:
            expected = tuple(json.loads(expected_snapshot))
        except (TypeError, json.JSONDecodeError) as exc:
            raise GateFailure("invalid_pending_snapshot") from exc
        if current != expected:
            raise GateFailure("pull_request_changed")
    return current


def run_validation(
    repository: str,
    event_name: str,
    event: Mapping[str, Any],
    ref: str,
    github: GitHubApi,
    jira: JiraClient,
    config: GateConfig,
    expected_snapshot: str | None = None,
) -> Mapping[str, Any]:
    config.validate()
    if repository.casefold() != EXPECTED_REPOSITORY.casefold():
        raise GateFailure("wrong_repository")
    _verify_event_repository(event, repository)
    _check_manual_ref(event_name, ref, event, github)
    number = _event_pr_number(event_name, event)
    initial = github.get_pull_request(number)
    if initial.get("number") != number:
        raise GateFailure("pull_request_number_mismatch")
    _validate_expected_snapshot(initial, expected_snapshot)
    tickets = validate_pr_structure(initial, repository, config)

    for ticket in tickets:
        try:
            issue = jira.get_issue(ticket)
            validate_issue(issue, config.field_id, config.target_version)
        except (GateFailure, JiraLookupFailure) as exc:
            raise GateFailure("jira_validation_failed") from exc

    fresh = github.get_pull_request(number)
    if snapshot_pr(fresh) != snapshot_pr(initial):
        raise GateFailure("pull_request_changed")
    validate_pr_structure(fresh, repository, config)
    return {
        "number": number,
        "head_sha": fresh["head"]["sha"],
        "mode": config.mode,
        "tickets_validated": len(tickets),
    }


def _status_description(config: GateConfig, passed: bool) -> str:
    if config.mode == "mock":
        return (
            "MOCK: synthetic target-version check passed"
            if passed
            else "MOCK: synthetic target-version check failed"
        )
    return (
        "Jira target-version check passed"
        if passed
        else "Jira target-version check failed"
    )


def run_from_environment(env: Mapping[str, str] = os.environ) -> int:
    requested_mode = env.get("JIRA_GATE_MODE", "mock").strip().lower()
    config = GateConfig(
        mode=requested_mode if requested_mode in {"mock", "live"} else "mock"
    )
    github: GitHubApi | None = None
    repository = env.get("GITHUB_REPOSITORY", "")
    pr_number: int | None = None
    try:
        config = GateConfig.from_env(env)
        if repository.casefold() != EXPECTED_REPOSITORY.casefold():
            raise GateFailure("wrong_repository")
        token = env.get("GITHUB_TOKEN", "")
        github = GitHubApi(repository, token)
        event_path = env.get("GITHUB_EVENT_PATH", "")
        with open(event_path, encoding="utf-8") as event_file:
            event = json.load(event_file)
        event_name = env.get("GITHUB_EVENT_NAME", "")
        _verify_event_repository(event, repository)
        pr_number = _event_pr_number(event_name, event)
        jira = create_jira_client(config)
        result = run_validation(
            repository=repository,
            event_name=event_name,
            event=event,
            ref=env.get("GITHUB_REF", ""),
            github=github,
            jira=jira,
            config=config,
            expected_snapshot=env.get("JIRA_GATE_PENDING_SNAPSHOT") or None,
        )
        github.create_status(
            result["head_sha"],
            "success",
            _status_description(config, True),
        )
        print(_status_description(config, True))
        return 0
    except Exception as exc:
        if github is not None:
            try:
                if pr_number is None:
                    event_path = env.get("GITHUB_EVENT_PATH", "")
                    with open(event_path, encoding="utf-8") as event_file:
                        event = json.load(event_file)
                    pr_number = _event_pr_number(env.get("GITHUB_EVENT_NAME", ""), event)
                fresh = github.get_pull_request(pr_number)
                sha = fresh.get("head", {}).get("sha")
                if isinstance(sha, str) and SHA_RE.fullmatch(sha):
                    github.create_status(
                        sha,
                        "failure",
                        _status_description(config, False),
                    )
            except Exception:
                pass
        if config.mode == "mock":
            print("MOCK: synthetic target-version check failed")
        else:
            print("Jira target-version check failed")
        if not isinstance(exc, (GateFailure, JiraLookupFailure)):
            print("Gate execution failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_from_environment())
