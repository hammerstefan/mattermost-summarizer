## Why

The orchestrator agent spends 32% of its wall time (182s of 571s) on `track_references` tool calls that require no LLM judgment:

1. **`classify_text` overhead**: The LLM calls `classify_text` with the full thread text (~44K chars) as a tool argument. The LLM echoes that text verbatim into its action output, permanently inflating the conversation context from ~10K to ~693K tokens and consuming ~3.3M input tokens over a session. URL classification is pure regex — no LLM judgment is involved.

2. **4-step bookkeeping overhead**: The LLM executes `is_followed` → `can_follow` → `mark_followed` → `increment_depth` per URL (12 round-trips for 3 URLs) despite no LLM judgment occurring between steps. Combined with 2 `classify_text` calls, this totals ~14 wasted round-trips and ~182s.

The root cause is architectural: the orchestrator agent runs as a single continuous `run()` loop, so Python has no opportunity to perform bookkeeping between delegation rounds without injecting state via callbacks. The callback-injection approach was investigated and confirmed SDK-safe (FIFOLock is reentrant), but all production-like SDK examples perform Python enrichment *before* `run()`, not inside callbacks. The dominant idiom is: Python pre-processes, calls `run()`, Python post-processes, calls `run()` again.

This change adopts that idiom: the orchestrator `run()` is split into per-depth segments separated by Python-driven URL classification and state tracking.

## What Changes

- `summarizer.py` drives a **depth loop**: at each depth, it calls `run()` with a `StopOnDelegate` pause condition, intercepts the delegation result, classifies URLs in Python, and re-enters `run()` with the classified URL list injected as the next user message
- `ReferenceTrackingTool` gains a single atomic `follow_url(url)` command replacing the 4-step `is_followed` / `can_follow` / `mark_followed` / `increment_depth` sequence
- `classify_text`, `is_followed`, `can_follow`, `mark_followed`, and `increment_depth` are removed from `track_references`
- The orchestrator prompt is updated to match the new interface
- `DelegateTool` is unchanged

## Capabilities

### New Capabilities

- `atomic-url-follow`: A single `follow_url` command on `track_references` that atomically checks followability, marks as followed, and increments depth — replacing the 4-step LLM sequence

### Modified Capabilities

- `recursive-reference-following`: URL classification moves to Python between `run()` segments; the 4-step bookkeeping protocol is replaced by `follow_url`; the orchestrator receives classified URLs as injected user messages rather than calling `classify_text`
- `orchestrator-agent`: The orchestrator `run()` is driven by a Python depth loop rather than a single continuous run; system prompt updated to remove `classify_text` instructions and replace 4-step protocol with `follow_url`

## Impact

- `src/mattermost_summarizer/summarizer.py`: replace single `run()` call with depth loop; add `_run_one_depth()` helper; add URL classification and injection between depths
- `src/mattermost_summarizer/subagents/reference_tracking_tool.py`: remove `classify_text`, `is_followed`, `can_follow`, `mark_followed`, `increment_depth`; add `follow_url`
- `src/mattermost_summarizer/agent.py`: update `ORCHESTRATOR_PROMPT` to remove `classify_text` instructions, replace 4-step protocol with `follow_url`, note that classified URLs are provided automatically
- No new dependencies; no API or config changes; `DelegateTool` unchanged
