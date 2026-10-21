# Role Assistant - AI-Powered Role Governance Tool

An AI-powered tool for analyzing SAP role assignments. Ask questions in natural language and get SQL-driven insights about duplicate roles, unused roles, overprivileged users, and more.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────┐     ┌──────────────┐
│   React + Vite  │────>│  ASP.NET Core    │────>│  OpenAI API  │     │  SQL Server  │
│   Frontend      │<────│  Web API         │<────│  (GPT-4o)    │     │  ProfileTailor│
│   :5173         │     │  :5199           │────>│              │     │              │
└─────────────────┘     └──────────────────┘     └──────────────┘     └──────────────┘
```

**Flow:**

1. User types a natural language question in the chat UI
2. Backend sends the question + database schema to OpenAI to generate a SQL SELECT query
3. Backend executes the query safely against SQL Server (SELECT only)
4. Backend sends results back to OpenAI to generate a human-readable summary
5. Frontend displays the summary, insights, data table, and the generated SQL

## Features

- **Natural Language Queries** - Ask about roles, users, permissions in plain English
- **Duplicate Role Detection** - Find roles with identical authorization sets
- **Unused Role Detection** - Identify roles not assigned to any user
- **Overprivileged User Detection** - Flag users with excessive role assignments
- **Expired Assignment Detection** - Find role assignments past their expiry date
- **Orphaned Assignment Detection** - Find assignments referencing non-existent roles
- **Role Distribution Analysis** - Breakdown by type and application area
- **User Risk Scoring** - Composite risk score based on role metrics
- **Category Filtering** - Focus queries on Roles, Users, User Groups, or Analysis
- **SQL Safety** - Only SELECT queries are allowed; dangerous keywords are blocked

## Prerequisites

- [.NET 9 SDK](https://dotnet.microsoft.com/download/dotnet/9.0)
- [Node.js 18+](https://nodejs.org/) (with npm)
- SQL Server with the `ProfileTailor` database
- OpenAI API key (from [platform.openai.com](https://platform.openai.com))

## Setup

### 1. Configure the Backend

Edit `backend/src/RoleAssistant.Api/appsettings.Development.json`:

```json
{
  "ConnectionStrings": {
    "ProfileTailor": "Server=YOUR_SERVER;Database=ProfileTailor;Trusted_Connection=True;TrustServerCertificate=True;"
  },
  "OpenAI": {
    "ApiKey": "sk-your-openai-api-key-here",
    "Model": "gpt-4o",
    "Endpoint": "https://api.openai.com/v1/chat/completions"
  }
}
```

**For Azure OpenAI**, change the endpoint:

```json
{
  "OpenAI": {
    "ApiKey": "your-azure-key",
    "Model": "your-deployment-name",
    "Endpoint": "https://your-resource.openai.azure.com/openai/deployments/your-deployment/chat/completions?api-version=2024-08-01-preview"
  }
}
```

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 3. Run from VS Code

Use the launch configurations in `.vscode/launch.json`:

- **Backend** - Builds and runs the .NET API on `http://localhost:5199`
- **Frontend** - Runs Vite dev server on `http://localhost:5173`
- **Full Stack (Backend + Frontend)** - Runs both simultaneously

Press `F5` or use the Run and Debug panel, select **"Full Stack (Backend + Frontend)"**.

### 4. Run from Terminal (alternative)

```bash
# Terminal 1 - Backend
cd backend/src/RoleAssistant.Api
dotnet run

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

## Usage

1. Type a question like _"Show me all users with more than 10 roles"_
2. Use the **category tabs** to focus on Roles, Users, User Groups, or Analysis
3. Click **Quick Analyses** in the sidebar for pre-built governance checks
4. Click **Show SQL Query** on any result to see the generated SQL
5. Data tables are scrollable and sortable

## Example Prompts

- "Which roles have the same authorization hash?"
- "Show users who haven't logged in for 90 days but still have active roles"
- "List all roles of type X assigned to users in the Finance department"
- "How many roles does each user group have on average?"
- "Find users with roles that expire in the next 30 days"

## Jira target-version gate proof of concept

This experiment is isolated under `.github/workflows/jira-target-version.yml` and
`tools/jira_gate/`. It does not change the application or any other repository.
It only validates open PRs targeting `test-jira-gate-2026.4.0` and compares the
configured single-select field's `value` with `2026.4.0` (the default field is
`customfield_12490`). It never reads Fix Version/s or falls back to another field.

The default mode is **mock**. `DEMO-101` is a deterministic synthetic match;
`DEMO-102`, `DEMO-103`, `DEMO-404`, and `DEMO-500` demonstrate a mismatch, absent
field, nonexistent issue, and synthetic API error. A `MOCK:` status is only an
enforcement demonstration; it is not evidence of live Jira integration. No Jira
credentials or network calls are needed for tests.

### Install and test

1. Review and merge this parser update into the repository's default `main`
   branch **before testing description parsing**; do not enable auto-merge.
   `pull_request_target` runs the installed trusted default-branch version,
   not the parser on a test PR's head. Manual runs must also select `main`.
   Use a separate, subsequent test PR.
2. After installation, create `test-jira-gate-2026.4.0` from `main` if it does
   not already exist. It remains the only test PR destination; `main` hosts the
   workflow, but is not a Jira-gated destination. The gate does not create
   branches or alter rulesets.
3. Create a test-only branch ruleset, initially **Disabled**, targeting exactly
   `test-jira-gate-2026.4.0`. Require the exact status context
   `jira-target-version`; the workflow job is named **Trusted Jira validator**.
   After its first run, select the status published by GitHub Actions as the
   expected source if the ruleset UI offers that choice. Enable the ruleset only
   after verifying the published context.
4. Keep baseline PR reviews, build checks, force-push restrictions, and deletion
   restrictions separate from this test gate. This is a personal public
   repository; do not assume an organization team exists or configure a team
   bypass. Test with a write collaborator who is not on any bypass list. The
   gate's proof does not require a bypass actor.
5. Open distinct-head test PRs with synthetic titles, then verify both the
   status and the ruleset's blocking behavior:

   | Synthetic PR title | Expected gate result |
   | --- | --- |
   | `DEMO-101: synthetic matching example` | `MOCK:` pass |
   | `DEMO-102: synthetic mismatch example` | `MOCK:` failure |
   | `DEMO-101 and DEMO-102: synthetic multiple-ticket example` | failure; every ticket must match |
   | `Synthetic title without a ticket` | failure unless the Jira section supplies tickets |
   | `DEMO-103: synthetic absent-field example` | failure |
   | `DEMO-404: synthetic nonexistent-ticket example` | failure |
   | `DEMO-500: synthetic API-error example` | failure |

   Also edit a title and description, push a new commit, and manually re-run **Jira target-version
   gate** from `main` with the PR number. The gate re-fetches current PR metadata,
   validates the current head SHA, and reports the exact status on that SHA.
   Confirm a matching status blocks/permits merging only as expected alongside
   the other rules.

### PR description format

Use this copyable synthetic section with an ordinary title such as
`Synthetic change`:

```markdown
## Jira tickets

[DEMO-101](https://example.atlassian.net/browse/DEMO-101) Synthetic change

## Notes

Non-authoritative discussion goes here.
```

The key renders as a clickable link followed by its summary. Plain `DEMO-101`,
bracketed `[DEMO-101]`, and
`<a href="https://example.atlassian.net/browse/DEMO-101">DEMO-101</a> Synthetic change`
also work. These URLs and tickets are examples only.

- The section starts at an ATX level-two heading `## Jira tickets` (label is
  case-insensitive; optional closing `##` is accepted). It ends at the next
  level-one or level-two heading, including Setext headings. Lower-level
  headings stay inside the section. Fenced-code headings do not start or end
  sections; keys inside an already active section are still validated.
- All matching sections are combined in document order. Incidental references
  outside them are ignored. Empty, missing, or null bodies supply no tickets.
- Title and section keys are combined, uppercased, and deduplicated. **Every
  key must match** the expected version. A matching body cannot override a
  mismatching title; neither source supplying a key fails.
- Keys must use the configured prefix and a positive one-to-nine-digit number.
  Malformed configured-prefix keys and wrong-prefix numeric keys fail in either
  source; they do not enable fallback to the other source.
- Link labels **and destinations** contribute keys, including percent-encoded
  or HTML-entity-encoded keys. If they differ, both must pass (or the malformed/
  wrong-prefix key fails). Repeating a key in a label and URL causes one lookup.
  Body URLs are never fetched; only identifiers go to the configured trusted
  Jira endpoint. Title and body are data, never executed.
- Limits: 512 title characters, 65,536 body characters, and ten unique keys
  across both sources. Oversized or non-string bodies fail closed.
- The pending, initial, and final metadata snapshots include the whole body
  (null/missing normalized to empty). Description changes during validation fail
  the run; the existing `edited` event starts revalidation after description edits.

### Optional private live-mode configuration

Live mode is opt-in and is not needed to install or test the mock gate. Because
this repository was **public** when this update was requested, do not assume it
has become private. Actions logs, PR text, and statuses may be public. Keep all
committed examples, fixtures, and public artifacts synthetic. Never commit
credentials, real corporate hostnames, ticket keys/titles, or private source.
Changing visibility is a manual owner decision, not performed by this update.

**Private visibility is not corporate authorization.** Obtain organizational
approval before connecting corporate Jira or storing its credentials. Private
repositories on a personal GitHub Free account do **not** support ruleset
enforcement; GitHub Pro is required for that private-repository demonstration.
A live lookup passing is not proof of enforced merge blocking. No visibility,
billing, ruleset, secret, or other repository settings are changed automatically.

Only after review and approval, configure trusted repository Actions variables:

| Variable | Purpose |
| --- | --- |
| `JIRA_GATE_MODE` | Set to `live`; unset defaults to `mock` |
| `JIRA_BASE_URL` | Approved HTTPS Jira base URL, with no path, query, or fragment |
| `JIRA_ALLOWED_HOST` | Exact lowercase hostname approved for `JIRA_BASE_URL` |
| `JIRA_GATE_VERSION` | Expected option text; defaults to `2026.4.0` |
| `JIRA_FIELD_ID` | Custom field ID; defaults to `customfield_12490` |
| `JIRA_TICKET_PREFIX` | Approved title/section ticket prefix; defaults to synthetic `DEMO` |

Add Actions secrets `JIRA_EMAIL` and `JIRA_API_TOKEN` for a read-only Jira service
account. Configure the real prefix and approved Jira URL privately in repository
settings; do not put either in a commit or PR. The workflow only makes bounded
HTTPS GET requests to the exact approved host, rejects redirects, and emits
generic live-mode status/log messages. Live validation rejects fork PRs; there
is no public-fork Jira lookup policy in this proof of concept.

**Authentication compatibility:** the existing client supports an HTTPS site
root plus `/rest/api/3`, using email + an **unscoped site API token**, only if
approved by your organization. Scoped Atlassian API tokens require
`https://api.atlassian.com/ex/jira/{cloudId}`, which this client's site-root URL
validator rejects. Scoped-gateway support is not implemented here and needs a
separate follow-up. Do not weaken organizational token policy; if scoped tokens
are required, stop before enabling live mode.

After the parser update is merged into `main`:

1. Confirm privacy, organizational authorization, compatible authentication, and
   the account plan/enforcement prerequisites above. Leave mock mode enabled
   until these are resolved.
2. In **Settings → Secrets and variables → Actions**, set the approved values
   for the five non-mode variables above and add the two secrets. `JIRA_EMAIL`
   is a **secret**, not a variable. Use an approved least-privilege read account.
   Set `JIRA_GATE_MODE=live` **last**.
3. In the approved private testing context only, prepare an authorized test
   issue with `customfield_12490.value` equal to `2026.4.0` (or your explicitly
   configured field/version). Do not copy corporate details to public artifacts.
4. Open or edit a same-repository PR into `test-jira-gate-2026.4.0`, using the
   approved key in its title or the exact Jira section above. Do not use a fork.
5. Choose **Actions → Jira target-version gate → Run workflow**, select **main**,
   and enter that open PR's number. It fetches actual current PR metadata,
   rather than trusting a stale event title/body. Look for the exact
   `jira-target-version` status and the generic message
   `Jira target-version check passed` without `MOCK:`.
6. Repeat with an authorized mismatching version and verify failure and merge
   blocking as a non-bypass user. Manually dispatch again after **configuration
   or Jira-only changes**: neither automatically starts a PR workflow.
   Switch `JIRA_GATE_MODE` back to `mock` when finished and revalidate.

### Limits

Jira-only field changes do not generate PR events. Manual revalidation is
supported, but a previous pass can become stale until it is run. The status is
a snapshot, not continuous or atomic merge-time Jira validation; a Jira change
or PR update can race a merge. Duplicate PRs sharing the same head SHA also
share a commit-status context, so their independent results cannot be isolated
by this status alone. These limitations must be addressed before any production
rollout; this proof of concept does not configure the production branch.

The workflow uses `pull_request_target` only for trusted default-branch code:
it checks out the workflow revision, never the PR head, and does not run PR
dependencies. Manual dispatch is rejected unless selected from the current
default branch. GitHub's public-fork approval controls for ordinary
`pull_request` workflows are not a safety net for this privileged event; review
the repository's Actions event policy and confirm `pull_request_target` is
allowed. GitHub documents a default public-repository policy for this event
with enforcement scheduled for November 2, 2026 for affected repositories.
See GitHub's documentation on
[pull_request_target](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target),
[manually running workflows](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow),
[approving fork workflow runs](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/approve-runs-from-forks),
and [commit statuses](https://docs.github.com/en/rest/commits/statuses).

## Project Structure

```
Hackathon/
├── .vscode/
│   ├── launch.json          # Debug configurations
│   └── tasks.json           # Build tasks
├── backend/
│   ├── RoleAssistant.sln    # .NET solution file
│   └── src/
│       └── RoleAssistant.Api/
│           ├── Controllers/
│           │   ├── ChatController.cs       # NL chat endpoint
│           │   └── AnalysisController.cs   # Pre-built analyses
│           ├── Models/
│           │   └── ChatModels.cs           # Request/response DTOs
│           ├── Services/
│           │   ├── AiService.cs            # OpenAI integration
│           │   ├── RoleAnalysisService.cs  # Pre-built SQL queries
│           │   ├── SchemaProvider.cs       # DB schema for AI context
│           │   └── SqlExecutionService.cs  # Safe SQL execution
│           ├── Program.cs
│           └── appsettings.json
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Main chat UI component
│   │   ├── api.ts            # API client
│   │   ├── index.css         # Styles
│   │   └── main.tsx          # Entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts        # Dev server + API proxy
└── TableSchema/              # Reference SQL table definitions
    ├── RoleTypes.sql
    ├── SapRoles.sql
    ├── SapUserRoles.sql
    ├── UserGroups.sql
    └── Users.sql
```
