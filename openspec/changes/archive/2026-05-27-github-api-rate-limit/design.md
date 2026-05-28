## Context

The `FetchGitHubIssueExecutor` in `fetch_github_issue/impl.py` uses an `httpx.Client` configured in the `client` property with `timeout=30.0` but no retry limits. On HTTP 403/429 responses, the executor Catches `httpx.HTTPStatusError`, logs the event, and returns an immediate error observation — no retry is attempted.

GitHub's API returns:
- **429 Too Many Requests** with a `Retry-After` header (seconds to wait)
- **403 Forbidden** (may indicate rate limit or token issues)

Authenticated requests get 5,000 req/hour; unauthenticated get 60/hour. Exhausting the limit prematurely wastes available quota and requires manual intervention.

## Goals / Non-Goals

**Goals:**
- Retry on 403/429 GitHub API responses with exponential backoff
- Respect `Retry-After` header when present on 429
- Fall back to exponential backoff (1s, 2s, 4s, 8s) when `Retry-After` is absent
- Limit retry attempts to 3 to avoid hanging indefinitely
- Use `httpx.Limits` for connection pool configuration

**Non-Goals:**
- Changing the tool's action/observation interface (no new parameters)
- Implementing retry for other tools (Launchpad, Mattermost threads)
- Replacing httpx with another HTTP client

## Decisions

### 1. Retry strategy: exponential backoff with `Retry-After` priority

**Decision:** On 429 (rate limited) or 403 (forbidden), attempt up to 3 retries with exponential backoff.

- If the response has a `Retry-After` header, use its value (parsed as seconds) for the first wait
- If no `Retry-After`, use exponential backoff: 1s → 2s → 4s → 8s (capped)
- After 3 failed retries, return a user-friendly error: "GitHub API rate limit exceeded. Configure github_token in your config to increase limits."

**Rationale:** This matches GitHub's documented behavior and is simple to implement. Alternatives considered:
- Using `httpx-retries` middleware — adds a dependency; exponential backoff is simple enough to hand-roll
- Immediate retry (no backoff) — increases likelihood of continued rejection
- Limiting retries to 1 — insufficient for transient GitHub rate limit windows

**Trade-off:** Retry logic adds latency on rate-limited requests. Unavoidable given the API semantics.

### 2. Client-level retry vs. request-level retry

**Decision:** Implement retry logic inside `__call__` before returning the error observation, not via `httpx`'sbuilt-in retry configuration.

**Rationale:** The executor's error path already returns structured `FetchGitHubIssueObservation(error=...)`. Wrapping retry at the call site keeps the control flow explicit. `httpx.Client` doesn't natively support per-status-code retry callbacks without a custom transport — request-level retry is cleaner here.

### 3. Connection pool limits

**Decision:** Configure `httpx.Limits(max_connections=10, max_keepalive_connections=5)` on the client.

**Rationale:** Maintains connection reuse efficiency. Existing executor is a single-client singleton — connection limits don't materially affect behavior today but future-proof if concurrency increases.

## Risks / Trade-offs

- **[Risk]** Retry adds latency (up to ~15s worst case on 3 exponential backoffs) → **Mitigation:** Log each retry with remaining attempts; provide `retry_count` internal counter for debugging
- **[Risk]** `Retry-After` header value may be > int range → **Mitigation:** Cap at 60 seconds maximum wait per retry
- **[Risk]** HTTP 403 could mean invalid token (not just rate limit) → **Mitigation:** Only retry on explicitly recognized rate limit headers; if response body indicates auth failure, don't retry
- **[Trade-off]** Retry logic increases code complexity → **Mitigation:** Extract into a private `_fetch_with_retry()` method to keep `__call__` readable

## Migration Plan

1. Implement retry in `FetchGitHubIssueExecutor` with `uv sync` to pick up any new dependencies
2. No schema/API changes — observation fields identical
3. Deploy with existing rollout mechanism
4. Observe logs for retry events (`logger.info("Retrying GitHub API request for %s, attempt %d/%d")`)

No rollback needed — behavior is additive (retries happen only on 403/429).
