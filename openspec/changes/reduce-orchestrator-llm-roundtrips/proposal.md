## Why

The orchestrator agent spends 32% of its wall time (182s of 571s) on `track_references` tool calls that require no LLM judgment: URL classification (`classify_text`) and per-URL bookkeeping (`is_followed` → `can_follow` → `mark_followed` → `increment_depth`). Additionally, `classify_text` causes the LLM to echo ~40K tokens of raw thread content into its action output, permanently inflating the conversation context from ~10K to 693K tokens and costing ~3.3M input tokens per run. Both problems are architectural: pure Python operations are unnecessarily exposed as LLM-callable tools.

## What Changes

- A post-delegation callback registered in `summarizer.py` intercepts each `DelegateObservation`, runs `classify_urls_in_text()` in Python, and injects a compact classified URL list as a synthetic user message before the orchestrator LLM's next step — eliminating the `classify_text` tool call entirely
- `ReferenceTrackingTool` gains a single atomic `follow_url(url)` command that executes `has_been_followed` + `can_follow_deeper` + `mark_followed` + `increment_depth` in one Python call, replacing the current 4-step LLM sequence per URL
- `classify_text`, `is_followed`, `can_follow`, `mark_followed`, and `increment_depth` commands are removed from the `track_references` tool
- `DelegateTool` is unchanged
- The orchestrator prompt is updated to reflect the new flow

## Capabilities

### New Capabilities

- `atomic-url-follow`: A single `follow_url` command on `track_references` that atomically checks, marks, and increments depth for a URL, replacing the 4-step sequence

### Modified Capabilities

- `recursive-reference-following`: URL classification moves out of the LLM loop entirely — classified URLs are injected automatically after each delegation; the 4-step per-URL bookkeeping protocol is replaced by `follow_url`
- `orchestrator-agent`: System prompt updated to reflect the new flow — classified URLs arrive as injected messages; the LLM uses `follow_url` to register interest in a URL before delegating

## Impact

- `src/mattermost_summarizer/subagents/reference_tracking_tool.py`: remove `classify_text`, `is_followed`, `can_follow`, `mark_followed`, `increment_depth`; add `follow_url`
- `src/mattermost_summarizer/summarizer.py`: add `_post_delegation_callback` closure; pass it in the `callbacks` list to `LocalConversation`
- `src/mattermost_summarizer/agent.py`: update `ORCHESTRATOR_PROMPT` to remove `classify_text` instructions, replace 4-step protocol with `follow_url`, note that classified URLs are injected automatically
- No new dependencies; no API or config changes
