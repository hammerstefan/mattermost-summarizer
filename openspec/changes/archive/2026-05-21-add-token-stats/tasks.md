## 1. Data Model Updates

- [x] 1.1 Update `SummaryMeta` in `src/mattermost_summarizer/models.py` to include `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, and `reasoning_tokens` fields with default values of 0.

## 2. String Formatting Implementation

- [x] 2.1 Create a helper function in `SummaryResult` or `utils.py` to format token numbers (use `K` suffix for `>= 1000` with 2 decimal places, exact integer otherwise).
- [x] 2.2 Update `SummaryResult.__str__` in `src/mattermost_summarizer/models.py` to remove the standalone `LLM cost:` line.
- [x] 2.3 Add logic in `SummaryResult.__str__` to build the new `Tokens:` line string.
- [x] 2.4 Incorporate dynamic visibility into the string builder: omit `cache hit` and `reasoning` if their values calculate to exactly 0.
- [x] 2.5 Place the final `Tokens:` line at the very bottom of the metadata block in `SummaryResult.__str__`.

## 3. Data Extraction Updates

- [x] 3.1 In `src/mattermost_summarizer/summarizer.py`, modify `MattermostSummarizer.summarize()` to extract `prompt_tokens`, `completion_tokens`, `cache_read_tokens`, `cache_write_tokens`, and `reasoning_tokens` from `agent.llm.metrics.accumulated_token_usage` (defensively handle missing attributes).
- [x] 3.2 Pass the extracted token usage values into the `SummaryMeta` constructor when creating the `SummaryResult`.

## 4. Tests and Verification

- [x] 4.1 Update existing metadata format tests in `tests/test_models.py` to pass with the removed `LLM cost:` line and the new `Tokens:` footer.
- [x] 4.2 Add test case in `tests/test_models.py` validating the `K` suffix formatting on large token counts.
- [x] 4.3 Add test case in `tests/test_models.py` validating the exact integer formatting on small token counts.
- [x] 4.4 Add test case in `tests/test_models.py` verifying that zero-value reasoning and cache hit segments are correctly omitted from the output.
- [x] 4.5 Run `uv run pytest` to ensure all tests pass.
- [x] 4.6 Run `uv run ruff check .` and `uv run mypy .` / `uv run pyright` to verify static analysis compliance.
