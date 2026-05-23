## 1. Atomic follow_url command

- [ ] 1.1 Add `follow_url(url)` to `ReferenceTrackingExecutor` in `reference_tracking_tool.py` — atomically checks `has_been_followed`, `can_follow_deeper`, `mark_followed`, `increment_depth` under `tracker.lock()`; returns outcome string `success | already_followed | depth_exceeded`
- [ ] 1.2 Remove `is_followed`, `can_follow`, `mark_followed`, `increment_depth` command branches from `ReferenceTrackingExecutor.__call__`
- [ ] 1.3 Remove `classify_text` command branch from `ReferenceTrackingExecutor.__call__`
- [ ] 1.4 Update `ReferenceTrackingTool.create()` description string to document only `follow_url`, `classify`, `reset`
- [ ] 1.5 Update `ReferenceTrackingObservation` fields — remove fields only used by removed commands (`is_followed`, `can_follow_deeper` if unused); add `outcome: str | None`

## 2. Python depth loop in summarizer.py

- [ ] 2.1 Add `_pause_after_delegation_callback` factory function (returns a closure) in `summarizer.py` — guards on `isinstance(event, ObservationEvent) and isinstance(event.observation, DelegateObservation) and event.observation.command == "delegate"` (not `"spawn"`, which also produces a `DelegateObservation`); calls `conv.pause()` once; sets a fired-flag that is reset before each `conv.run()` call to re-arm for the next depth segment
- [ ] 2.2 Replace the single `conversation.run()` call in `MattermostSummarizer.summarize()` with a `_run_depth_loop()` helper that iterates: arm callback → `run()` → extract last `DelegateObservation` text → classify URLs → inject message if any → repeat until finish or no new URLs
- [ ] 2.3 Implement `_extract_last_delegate_observation(conversation)` helper — scans `conversation.state.events` in reverse for the most recent `ObservationEvent` where `isinstance(event.observation, DelegateObservation)` and `event.observation.command == "delegate"`; extracts text as `"".join(c.text for c in event.observation.to_llm_content if hasattr(c, "text"))` (same pattern as `_extract_finish_action`)
- [ ] 2.4 Implement `_format_url_injection_message(classified_urls, tracker)` helper — formats the classified URL list message with depth info
- [ ] 2.5 Construct `ReferenceTracker(max_depth=max_reference_depth)` in `MattermostSummarizer.summarize()` and pass it to `build_orchestrator_agent()` as a new `tracker` keyword argument; update `build_orchestrator_agent` signature to accept and forward it to `ReferenceTrackingTool.create(tracker)`. This gives the depth loop direct access to the same tracker instance used by `ReferenceTrackingExecutor`.

## 3. Orchestrator prompt update

- [ ] 3.1 Update `ORCHESTRATOR_PROMPT` in `agent.py` — remove `classify_text` instructions; replace 4-step bookkeeping section with `follow_url` usage instructions; add note that classified URL lists are injected automatically as user messages after each delegation

## 4. Tests

- [ ] 4.1 Update `ReferenceTrackingExecutor` unit tests — add tests for `follow_url` (success, already_followed, depth_exceeded, concurrent atomicity); remove tests for deleted commands
- [ ] 4.2 Update orchestrator integration tests — verify no `classify_text` or `is_followed` / `can_follow` / `mark_followed` / `increment_depth` tool calls appear; verify `follow_url` is called before each delegation
- [ ] 4.3 Add unit test for `_pause_after_delegation_callback` — verify it fires once, pauses conversation, and does not fire again
- [ ] 4.4 Add unit test for `_extract_last_delegate_observation` and `_format_url_injection_message`
- [ ] 4.5 Run full test suite and fix any regressions: `uv run pytest -n auto`
