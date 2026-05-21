## Context

The Mattermost Summarizer agent produces structured summaries of conversation threads. Currently, the metadata section of the output only includes thread length, a high-level LLM cost estimation (`$0.0000`), model name, and execution duration. With the rising importance of prompt caching and context window optimization, users need deeper visibility into token usage metrics (input, output, cache read/write, and reasoning tokens). The OpenHands SDK already collects these metrics internally via `TokenUsage`, but they are not surfaced to the end user.

## Goals / Non-Goals

**Goals:**
- Extract granular token usage metrics from the OpenHands agent.
- Map the metrics to the `SummaryMeta` Pydantic model.
- Present the metrics in a highly readable, dense, and clean format replacing the current cost string.
- Provide a responsive layout that automatically omits zero-value stats (e.g., zero cache hits or zero reasoning tokens) to keep the CLI output clean.

**Non-Goals:**
- We are not changing how the OpenHands agent counts tokens; we are strictly consuming existing internal metric data.
- We are not changing the structure of the LLM provider configuration.
- We are not streaming the token metrics in real-time; they will be printed as part of the final summary.

## Decisions

### 1. Unified Token & Cost Line
**Decision:** Replace the standalone `LLM cost: $0.0000` line with a comprehensive `Tokens:` footer that also includes the total cost.
**Rationale:** Cost is directly tied to token usage. Grouping them on a single line (e.g., `Tokens: ↑ input 35.69K • cache hit 58.70% • reasoning 653 • ↓ output 1.82K • $ 0.00`) creates a cohesive overview and reduces vertical clutter.

### 2. Number Formatting Strategy
**Decision:** Implement a threshold-based number formatting logic: values `>= 1000` will be divided by 1000, given two decimal places, and suffixed with `K` (e.g., `35.69K`). Values `< 1000` will be exact integers (e.g., `653`).
**Rationale:** Context windows can reach over 100,000 tokens. Raw integers become difficult to parse at a glance. The `K` suffix optimizes readability without losing practical precision.

### 3. Handling Zero-Values
**Decision:** Dynamically omit the `cache hit` and `reasoning` segments from the formatted string if their underlying token count is exactly `0`.
**Rationale:** Many models (e.g., standard `gpt-4o`) do not emit reasoning tokens, and the first request in a session will naturally have a `0%` cache hit. Printing `cache hit 0.00%` or `reasoning 0` adds noise. Always showing input, output, and cost guarantees the baseline metrics are visible.

### 4. Cache Hit Percentage Calculation
**Decision:** The cache hit percentage will be calculated as `(cache_read_tokens / (input_tokens + cache_read_tokens)) * 100`. The denominator represents the total inbound prompt size.
**Rationale:** This standard formula reflects the percentage of the prompt that did not have to be re-processed by the model. 

### 5. Cost Precision
**Decision:** Reduce the cost formatting from 4 decimal places (`$0.0042`) to 2 decimal places (`$ 0.00`).
**Rationale:** Explicitly requested to match the specific UI design example. While some precision is lost for very cheap queries, it adheres strictly to the targeted aesthetic.

## Risks / Trade-offs

- **Risk:** OpenHands SDK changes its internal `Metrics` structure (e.g., `accumulated_token_usage` is moved or renamed).
  - *Mitigation:* Extract metrics defensively using `hasattr` or `.get()` with safe defaults so the program does not crash if the metric structure evolves.
- **Trade-off:** Losing 4-decimal precision on the total cost means very short summarizations might print `$ 0.00`.
  - *Mitigation:* Acceptable trade-off for UI cleanliness, as the `K` suffixed token values will clearly explain the scale of the request.
