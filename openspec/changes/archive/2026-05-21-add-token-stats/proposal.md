## Why

Token statistics (input, output, cache hits, and reasoning tokens) are vital for understanding the performance and cost-efficiency of LLM operations. Currently, the Mattermost Summarizer captures total thread length and dollar cost, but does not display fine-grained token usage metrics in its final output. By extracting this data from the OpenHands agent and displaying it, users gain better visibility into exactly how their budget and context window are being utilized.

## What Changes

- Add token usage fields (`input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `reasoning_tokens`) to the `SummaryMeta` Pydantic model.
- Modify the `SummaryResult.__str__` formatting logic to include a dedicated `Tokens:` line at the bottom of the METADATA section.
- Implement formatting rules:
  - Exact integers for values `< 1000`.
  - `K` suffix with two decimal places for values `>= 1000`.
  - Omission of `cache hit` and `reasoning` segments if they evaluate to exactly 0.
- Remove the standalone `LLM cost:` line and merge the cost (`$ 0.00`, 2 decimal places) into the new `Tokens:` line.
- Extract token data from `agent.llm.metrics.accumulated_token_usage` in the summarizer execution loop.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `mattermost-summarizer`: Updating REQ-011 to formally require token usage statistics (input, output, cache hits, reasoning) in the formatted output.

## Impact

- `src/mattermost_summarizer/models.py`: Model schema updates and string formatting logic.
- `src/mattermost_summarizer/summarizer.py`: Data extraction from the OpenHands `Metrics` system.
- `tests/test_models.py`: Updates to test output formatting rules (K-suffix, zero-value hiding).
