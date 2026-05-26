## 1. Logging Infrastructure Changes

- [x] 1.1 Add verbose mode flag to config parser (--verbose / MM_VERBOSE env var)
- [x] 1.2 Modify setup_logging() in utils.py to support optional stderr StreamHandler
- [x] 1.3 Add stderr StreamHandler when verbose mode is enabled
- [x] 1.4 Ensure file handler always receives all log levels regardless of stderr

## 2. fetch_github_issue/impl.py Updates

- [x] 2.1 Add logger.error with exc_info=True for unexpected exceptions
- [x] 2.2 Replace str(e) with generic message "An internal error occurred."
- [x] 2.3 Ensure rate limit (429/403) logs at info level, not warning
- [x] 2.4 Verify HTTP error for non-rate-limit 403 uses sanitized message

## 3. fetch_launchpad_bug/impl.py Updates

- [x] 3.1 Add logger.error with exc_info=True for unexpected exceptions
- [x] 3.2 Replace str(e) with generic message "An internal error occurred."
- [x] 3.3 Log HTTPError at warning level with sanitized details

## 4. fetch_file/impl.py Updates

- [x] 4.1 Add logger.error with exc_info=True for unexpected exceptions
- [x] 4.2 Replace str(e) with generic message "An internal error occurred."

## 5. fetch_thread/impl.py Updates

- [x] 5.1 Add logger.error with exc_info=True for unexpected exceptions
- [x] 5.2 Replace str(e) with generic message "An internal error occurred."

## 6. get_user/impl.py Updates

- [x] 6.1 Add logger.error with exc_info=True for unexpected exceptions
- [x] 6.2 Replace str(e) with generic message "An internal error occurred."

## 7. fetch_channel/impl.py Updates

- [x] 7.1 Add logger.error with exc_info=True for unexpected exceptions
- [x] 7.2 Replace str(e) with generic message "An internal error occurred."

## 8. fetch_reference_tool.py Updates

- [x] 8.1 Sanitize spawn_obs.to_llm_content error message before returning
- [x] 8.2 Replace raw LLM content with generic "Failed to spawn sub-agent" message
- [x] 8.3 Add logging for sub-agent spawn failures

## 9. critic.py Updates

- [x] 9.1 Change JSON parsing error feedback from f"parsing error: {e}" to generic string
- [x] 9.2 Log JSON parsing failures at debug level with exc_info=True

## 10. Testing

- [ ] 10.1 Add unit tests for sanitized error messages in each tool
- [ ] 10.2 Add integration test for verbose mode stderr output
- [ ] 10.3 Verify no raw exception strings appear in observation error fields
- [x] 10.4 Run ruff check and mypy on all modified files