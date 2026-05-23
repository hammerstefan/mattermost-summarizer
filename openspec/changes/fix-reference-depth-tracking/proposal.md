## Why

`ReferenceTracker.current_depth` counts every non-root `fetch_reference` call regardless of whether URLs are siblings (all found in the same thread) or nested (found inside another fetched reference). With `max_depth=3`, the 4th sibling URL from the root thread is blocked even though no nesting has occurred. This also means sibling URLs cannot each surface their own sub-references — one sibling's children consume depth slots that block other siblings. Additionally, the orchestrator's References block shows bare URLs with no surrounding context, leaving the orchestrator LLM to guess relevance from URL paths alone.

## What Changes

- **Replace depth model**: Drop the global `current_depth` counter. Track depth per-URL via a `dict[str, int]` on `ReferenceTracker` so siblings share the same depth and nesting depth matches the reference chain rather than total fetch count.
- **Pre-register pending URLs at injection time**: When `FetchReferenceExecutor` builds the References block after sub-agent completion, it registers each surfaced URL at its correct child depth (`parent_depth + 1`). On the next `fetch_reference` call, the executor looks up the registed depth — no LLM involvement in depth tracking.
- **Enrich References block with surrounding context**: Extract the sentence containing (or immediately adjacent to) each URL from the sub-agent result text. The orchestrator sees a one-line description per reference instead of a bare URL.
- **Update sub-agent prompts**: `THREAD_FETCHER_PROMPT`, `GITHUB_RESEARCHER_PROMPT`, and `BUG_RESEARCHER_PROMPT` gain an instruction to always write a one-sentence description near each URL they mention.
- **Remove `current_depth`, `increment_depth()` from `ReferenceTracker`**: Replaced by `register_pending(url, depth)` and depth lookup via `followed_urls` dict.
- **Update orchestration prompt**: `ORCHESTRATOR_PROMPT` reflects the enriched References block format and a simpler loop (decide relevance, call `fetch_reference`, repeat until no more references or block says depth limit reached).

## Capabilities

### New Capabilities
- `reference-context-enrichment`: Extracting one sentence of surrounding context per URL from sub-agent result text and injecting it into the References block, so the orchestrator can make informed relevance decisions.

### Modified Capabilities
- `recursive-reference-following`: Depth counting model changes from global sequential counter to per-URL parent-child nesting. `follow_url` / `depth_exceeded` / `already_followed` are replaced by pending registration and depth derived from the tracker. The References block format and injection mechanism change to include per-URL context.
- `orchestrator-agent`: The coordination prompt and loop description change to reflect the enriched References block format, and the explicit depth info presentation.

## Impact

- **Affected code**: `src/mattermost_summarizer/tools/reference_tracker.py` (data model), `src/mattermost_summarizer/subagents/fetch_reference_tool.py` (executor logic), `src/mattermost_summarizer/subagents/__init__.py` (prompts), `src/mattermost_summarizer/agent.py` (prompt)
- **Affected tests**: `tests/test_reference_tracker.py` (depth counter assertions), `tests/test_multi_agent.py` (Reference block format, depth scenario tests)
- **No API changes**: `max_depth` config remains in TOML
- **No breaking changes to external interfaces**: internal tracker API changes only
