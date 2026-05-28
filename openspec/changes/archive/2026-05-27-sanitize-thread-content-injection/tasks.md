## 1. Sanitization Utilities

- [x] 1.1 Create `src/mattermost_summarizer/sanitization.py` with `INJECTION_PATTERNS` blocklist (see design.md for patterns)
- [x] 1.2 Implement `sanitize_text(text: str) -> str` function that strips patterns and handles obfuscation
- [x] 1.3 Add `format_with_delimiter(content: str) -> str` function that wraps content in external content delimiters
- [x] 1.4 Add unit tests in `tests/test_sanitization.py` covering: obvious injection stripped, obfuscated stripped, legitimate content preserved

## 2. Input Sanitization — Thread Content

- [x] 2.1 Update `FetchThreadObservation.to_llm_content()` in `fetch_thread/impl.py` to call `sanitize_text()` on all message content before formatting
- [x] 2.2 Update `FetchThreadObservation.to_llm_content()` to wrap output with external content delimiter
- [x] 2.3 Run existing tests to verify no breakage: `uv run pytest tests/test_tools.py -v`

## 3. Input Sanitization — Other Tool Observations

- [x] 3.1 Apply sanitization to `FetchGitHubIssueObservation.to_llm_content()` in `fetch_github_issue/impl.py`
- [x] 3.2 Apply sanitization to `FetchLaunchpadBugObservation.to_llm_content()` in `fetch_launchpad_bug/impl.py`
- [x] 3.3 Apply sanitization to `FetchChannelObservation.to_llm_content()` in `fetch_channel/impl.py`

## 4. Output Validation — Finish Action Validators

- [x] 4.1 Add injection pattern detection to `coerce_tldr_to_str` in `levels/brief.py`
- [x] 4.2 Add injection pattern detection to `coerce_tldr_to_str` in `levels/normal.py`
- [x] 4.3 Add injection pattern detection to `coerce_tldr_to_str` in `levels/detailed.py`
- [x] 4.4 Each validator SHALL log a WARNING (not block) when a pattern is matched

## 5. Preamble in Initial User Message

- [x] 5.1 Update `summarizer.py` line 146-148 to wrap `thread_text` with external content delimiter in the initial `send_message()` call

## 6. Verification

- [x] 6.1 Run linting: `uv run ruff check .`
- [x] 6.2 Run type checking: `uv run mypy .`
- [x] 6.3 Run tests: `uv run pytest -n auto`
- [x] 6.4 Update `SECURITY_AUDIT_TODOS.md` — mark issue #5 as Done