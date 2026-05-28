# Spec: GitHub API Rate Limit Handling

## Capability

Handle GitHub API rate limit (HTTP 429/403) responses with retry logic using exponential backoff and `Retry-After` header support.

## Requirements

### Requirement: GitHub API rate limit retry with exponential backoff

The system SHALL retry GitHub API requests that receive HTTP 403 or 429 responses with exponential backoff before returning an error.

- The system SHALL support up to 3 retry attempts on rate-limited responses
- The system SHALL prefer use the `Retry-After` header value when present on 429 responses, capped at 60 seconds
- The system SHALL fall back to exponential backoff (1s, 2s, 4s, 8s) when `Retry-After` is absent
- The system SHALL return a user-friendly error observation only after all retry attempts are exhausted
- The system SHALL log each retry attempt with the URL, attempt number, and wait duration

### Requirement: Rate limit detection

The system SHALL distinguish between rate limit responses and authentication failures.

- The system SHALL retry only on responses explicitly indicating rate limiting (429 with `Retry-After`, or 403 on known rate-limited endpoints)
- The system SHALL NOT retry when the response body indicates invalid credentials or authentication failure

#### Scenario: Successful retry with Retry-After header
- **WHEN** GitHub API returns HTTP 429 with `Retry-After: 5`
- **THEN** the system waits 5 seconds and retries the request, up to 3 attempts total
- **AND** each retry is logged at INFO level

#### Scenario: Retry with exponential backoff (no Retry-After)
- **WHEN** GitHub API returns HTTP 429 without `Retry-After` header
- **THEN** the system waits 1s, then 2s, then 4s between retry attempts
- **AND** each retry is logged at INFO level

#### Scenario: All retries exhausted
- **WHEN** all 3 retry attempts are exhausted without success
- **THEN** the observation contains error: "GitHub API rate limit exceeded. Configure github_token in your config to increase limits."

#### Scenario: Authentication failure (no retry)
- **WHEN** GitHub API returns HTTP 403 with response body indicating invalid credentials
- **THEN** the system returns immediately without retry
- **AND** the error message is user-friendly without exposing internal details
