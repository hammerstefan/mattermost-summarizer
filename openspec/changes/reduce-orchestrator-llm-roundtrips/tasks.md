## 1. Refactor ReferenceTrackingTool

- [ ] 1.1 Add `follow_url` command to `ReferenceTrackingExecutor` in `reference_tracking_tool.py`: atomically run `has_been_followed` check, `can_follow_deeper` check, `mark_followed`, and `increment_depth` under `tracker.lock()`; return distinct results for success / already-followed / depth-exceeded
- [ ] 1.2 Remove `classify_text`, `is_followed`, `can_follow`, `mark_followed`, and `increment_depth` command handlers from `ReferenceTrackingExecutor`
- [ ] 1.3 Update `ReferenceTrackingTool.create()` description string to advertise only `follow_url`, `classify` (single URL), and `reset`
- [ ] 1.4 Update `ReferenceTrackingObservation` fields: add `already_followed: bool | None` and `depth_exceeded: bool | None`; remove fields only populated by removed commands

## 2. Add Post-Delegation Callback

- [ ] 2.1 Confirm the attribute on `DelegateObservation` that holds result text (inspect `to_llm_content` in `delegate_tool.py` / SDK)
- [ ] 2.2 Implement `_post_delegation_callback(event)` closure in `summarizer.py`: guard with `isinstance(obs, DelegateObservation)`, call `classify_urls_in_text(obs_text, tracker)`, format results, call `conv_ref[0].send_message(...)` if any URLs found
- [ ] 2.3 Pass `_post_delegation_callback` alongside `_on_finish_callback` in the `callbacks` list when constructing `LocalConversation`
- [ ] 2.4 Verify callback does not inject a message when delegation observation contains no followable URLs

## 3. Update Orchestrator Prompt

- [ ] 3.1 In `agent.py`, remove all `classify_text` instructions from `ORCHESTRATOR_PROMPT`
- [ ] 3.2 Remove the 4-step per-URL protocol; replace with a single `follow_url(url)` call description
- [ ] 3.3 Add a note that classified URL lists are injected automatically after each delegation and the LLM should use them to decide relevance

## 4. Update Tests

- [ ] 4.1 Remove or update tests that exercise removed commands (`classify_text`, `is_followed`, `can_follow`, `mark_followed`, `increment_depth`) via `ReferenceTrackingExecutor`
- [ ] 4.2 Add unit tests for `follow_url`: success path, already-followed path, depth-exceeded path
- [ ] 4.3 Add unit test for post-delegation callback: mock a `DelegateObservation` with known URLs, assert `send_message` is called with a correctly formatted message
- [ ] 4.4 Add unit test for post-delegation callback: mock a `DelegateObservation` with no followable URLs, assert `send_message` is NOT called

## 5. Verification

- [ ] 5.1 Run `uv run ruff check .` and fix any linting issues
- [ ] 5.2 Run `uv run mypy .` and fix any type errors
- [ ] 5.3 Run `uv run pytest -n auto` and confirm all tests pass
