## Why

Tool executors catch exceptions broadly and return raw exception messages (`str(e)`) to the LLM via the `error` field in observations. This exposes internal details like file paths, network configuration, and API response structures. Additionally, operators have no stderr visibility during normal operation—all logging goes exclusively to the log file.

## What Changes

- **Logging verbosity ladder**: Map error types to appropriate log levels (debug/info/warning/error)
  - Rate limits (429/403): `log.info` — expected behavior, no operator action needed
  - Network timeouts: `log.warning` — may indicate connectivity issues
  - Unexpected exceptions: `log.error` with full traceback — requires attention
- **Dual output**: Logs written to file always; stderr output enabled only in verbose/debug mode
- **Sanitized error messages**: LLM receives generic user-safe messages ("An internal error occurred") instead of raw exception strings
- **Critic feedback path**: JSON parsing errors in critic logged but not reflected into feedback string

## Capabilities

### New Capabilities
- `tool-error-sanitization`: Unified error handling pattern for all tool executors with proper logging verbosity, file+stderr output, and sanitized LLM-facing messages

### Modified Capabilities
- None (implementation change only, no spec-level behavior changes)

## Impact

- **Files modified**: `fetch_github_issue/impl.py`, `fetch_launchpad_bug/impl.py`, `fetch_file/impl.py`, `fetch_thread/impl.py`, `get_user/impl.py`, `fetch_channel/impl.py`, `fetch_reference_tool.py`, `critic.py`
- **No API changes**: Observation error fields remain, values change from raw to sanitized
- **No breaking changes**: Tool behavior from LLM perspective unchanged except message content