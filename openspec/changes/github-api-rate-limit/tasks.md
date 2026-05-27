## 1. Read Existing Implementation

- [x] 1.1 Review `fetch_github_issue/impl.py` client property and `__call__` method
- [x] 1.2 Identify all HTTP request methods that need retry logic (`_fetch_issue`, `_fetch_comments`, `_fetch_review_comments`)

## 2. Implement Retry Logic

- [x] 2.1 Add `time` import and private `_wait_and_retry` helper method to `FetchGitHubIssueExecutor`
- [x] 2.2 Modify `_fetch_issue` to call retry wrapper instead of direct `client.get`
- [x] 2.3 Update client property to include `httpx.Limits(max_connections=10, max_keepalive_connections=5)`
- [x] 2.4 Update `__call__` error handling to retry on 403/429 before returning error observation
- [x] 2.5 Extract `Retry-After` header value when present (capped at 60s per retry)
- [x] 2.6 Fall back to exponential backoff (1s, 2s, 4s, 8s) when `Retry-After` absent

## 3. Logging

- [x] 3.1 Add INFO-level log entries for each retry attempt (URL, attempt number, wait duration)
- [x] 3.2 Log final error after all retries exhausted

## 4. Verification

- [x] 4.1 Run `uv run ruff check src/mattermost_summarizer/tools/fetch_github_issue/`
- [x] 4.2 Run `uv run pyright src/mattermost_summarizer/tools/fetch_github_issue/`
- [x] 4.3 Run `uv run pytest -n auto` to confirm no regressions