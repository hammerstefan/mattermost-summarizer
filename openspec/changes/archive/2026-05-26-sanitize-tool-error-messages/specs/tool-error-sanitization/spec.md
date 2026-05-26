# Spec: Tool Error Sanitization

## Capability

Provide unified error handling for all tool executors that sanitizes error messages sent to the LLM while maintaining full debugging information in logs.

## Requirements

### Requirement: Sanitized error messages for LLM

All tool executors SHALL return user-safe, sanitized error messages via the `error` field in observations. Raw exception strings SHALL NOT be exposed to the LLM.

The system SHALL use the following generic error messages:
- `"An internal error occurred."` — for unexpected exceptions
- `"Failed to fetch GitHub resource."` — for GitHub fetch failures
- `"Failed to fetch Launchpad bug."` — for Launchpad fetch failures
- `"Failed to fetch channel."` — for channel fetch failures
- `"Failed to fetch user."` — for user fetch failures
- `"Failed to fetch file."` — for file fetch failures
- `"Failed to fetch thread."` — for thread fetch failures
- `"Failed to fetch reference."` — for reference fetch failures

#### Scenario: Generic message on unexpected exception
- **WHEN** a tool executor catches an unexpected `Exception` during execution
- **THEN** the observation's `error` field SHALL contain only the generic message
- **THEN** the raw exception string SHALL NOT be present in the error field

#### Scenario: Rate limit error uses predefined message
- **WHEN** GitHub API returns 429 rate limit exceeded
- **THEN** error field SHALL be `"GitHub API rate limit exceeded. Configure github_token in your config to increase limits."`
- **AND** the message SHALL be user-safe (no internal details)

### Requirement: Logging verbosity ladder

Tool executors SHALL use appropriate log levels for different error scenarios:

| Scenario | Log Level | Output |
|----------|-----------|--------|
| Rate limited (429/403) | `log.info` | File only (normal), stderr in verbose |
| Invalid URL format | `log.debug` | File only |
| Network timeout | `log.warning` | File + stderr in verbose |
| Unexpected exception | `log.error` with `exc_info=True` | File + stderr in verbose |

#### Scenario: Rate limit logs at info level
- **WHEN** GitHub API returns 429
- **THEN** logger SHALL log at `info` level with message "GitHub API rate limited"
- **AND** no stack trace is included

#### Scenario: Unexpected exception logs with traceback
- **WHEN** tool executor catches an unexpected exception
- **THEN** logger SHALL log at `error` level with `exc_info=True`
- **AND** full traceback SHALL be written to log file
- **AND** in verbose mode, full traceback goes to stderr

### Requirement: File-based logging with optional stderr

All tool executors SHALL write logs to the configured log file. Stderr output SHALL be controlled by verbosity level:

- **Normal mode**: All log levels → file only (no stderr output)
- **Verbose mode (`-v`)**: `info`, `warning`, `error` → stderr + file; `debug` → file only

#### Scenario: Verbose mode enables stderr for warnings
- **WHEN** verbosity level is verbose and a network timeout occurs
- **THEN** warning message SHALL be written to both stderr and log file
- **AND** operators see the message in real-time

#### Scenario: Normal mode suppresses stderr
- **WHEN** verbosity level is normal and an error occurs
- **THEN** error message SHALL be written to log file only
- **AND** no output appears on stderr

### Requirement: Critic feedback sanitization

The critic SHALL NOT include raw exception strings in feedback messages.

When JSON parsing fails in critic evaluation:
- **WHEN** `json.JSONDecodeError`, `ValueError`, or `AttributeError` occurs during response parsing
- **THEN** logger SHALL log at `debug` level with the exception details
- **AND** feedback SHALL be set to `"Critic evaluation failed due to parsing error. Assuming fair quality."`
- **AND** no exception details SHALL appear in the feedback string

#### Scenario: JSON parse failure uses generic feedback
- **WHEN** LLM returns malformed JSON in critic response
- **THEN** feedback field SHALL contain generic message only
- **AND** exception type/name SHALL NOT be in the feedback string

### Requirement: Error message consistency

All tool executors SHALL use consistent patterns for error messages:

- HTTP errors: `"<Service> error: <generic description>"` (no status codes or URL details)
- Network errors: `"Connection failed. Check network connectivity."`
- Auth errors: `"Authentication failed. Check credentials."`
- Not found: `"Resource not found or access denied."`

#### Scenario: HTTP error without exposing internals
- **WHEN** HTTPStatusError occurs with status 500
- **THEN** error message SHALL be `"GitHub API error. Try again later."`
- **AND** status code 500 SHALL NOT appear in the message

#### Scenario: Network error sanitized
- **WHEN** httpx.RequestError occurs (connection timeout, DNS failure)
- **THEN** error message SHALL be `"Connection failed. Check network connectivity."`
- **AND** no IP addresses, hostnames, or port numbers SHALL appear