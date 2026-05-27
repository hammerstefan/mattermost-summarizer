## Why

The `FetchGitHubIssueExecutor` currently returns an error on GitHub API 403/429 rate limit responses without retrying. This wastes available quota when authenticated tokens are configured and provides a poor user experience. GitHub's API supports `Retry-After` headers and standard exponential backoff patterns — we should respect them.

## What Changes

- Add exponential backoff retry logic for GitHub API calls that receive 403/429 responses
- Respect the `Retry-After` header when present in 429 responses
- Fall back to exponential backoff (1s, 2s, 4s, 8s) when `Retry-After` is absent
- Configurable maximum retry attempts via `httpx.Limits`
- Return a user-friendly error only after all retries are exhausted

## Capabilities

### New Capabilities

- `github-api-rate-limit`: Retry logic with exponential backoff for `fetch-github-issue` tool

### Modified Capabilities

- `fetch-github-issue`: Behavior extended to retry on rate limit responses rather than failing immediately

## Impact

**Affected code:**
- `src/mattermost_summarizer/tools/fetch_github_issue/impl.py` — executor retry logic and client configuration

**No external API changes** — the tool's action/observation interface remains identical.

**Dependencies:** `httpx` (already in use)
