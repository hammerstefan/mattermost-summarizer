## 1. Update ReferenceTracker data model

- [x] 1.1 Replace `followed_urls: set[str]` with `followed_urls: dict[str, int]` (url → depth fetched at)
- [x] 1.2 Add `pending_urls: dict[str, int]` field (url → child depth, populated at injection time)
- [x] 1.3 Add `register_pending(url: str, depth: int)` method
- [x] 1.4 Add `get_depth_for(url: str) -> int | None` method (checks pending then followed)
- [x] 1.5 Update `mark_followed(url: str, depth: int)` to accept depth and populate dict
- [x] 1.6 Remove `current_depth: int` field
- [x] 1.7 Remove `can_follow_deeper()` method
- [x] 1.8 Remove `increment_depth()` method
- [x] 1.9 Update `reset()` to clear both `followed_urls` and `pending_urls`
- [x] 1.10 Update `__all__` exports

## 2. Implement sentence context extraction

- [x] 2.1 Add `extract_sentence_context(text: str, url: str) -> str` to `reference_tracker.py`
- [x] 2.2 Support: URL in middle of sentence (return containing sentence)
- [x] 2.3 Support: URL at start of sentence (return that sentence)
- [x] 2.4 Support: URL preceded by text on previous line (return preceding sentence)
- [x] 2.5 Fallback: return `"(no description available)"` if no sentence boundary within 300 chars
- [x] 2.6 Strip URL from returned context (avoid duplicating it in the References block)

## 3. Update FetchReferenceExecutor

- [x] 3.1 Replace `can_follow_deeper()` check with depth-based check: `get_depth_for(action.url) >= max_depth` → error (root URLs return `None` → 0, always passes)
- [x] 3.2 At injection time: call `tracker.register_pending(url, depth=parent_depth + 1)` for each followable URL before building the block
- [x] 3.3 Call `tracker.mark_followed(action.url, depth)` with the correct depth (from `get_depth_for`, defaulting to 0 for root)
- [x] 3.4 Remove `is_root_fetch` guard and `increment_depth()` call — depth is registered per-URL, not incremented globally
- [x] 3.5 Update `build_reference_following_prompt` call to enrich each URL entry with a context sentence from `extract_sentence_context`
- [x] 3.6 Ensure `classify_urls_in_text` still excludes already-followed URLs

## 4. Update sub-agent prompts

- [x] 4.1 Add link description instruction to `THREAD_FETCHER_PROMPT`
- [x] 4.2 Add link description instruction to `GITHUB_RESEARCHER_PROMPT`
- [x] 4.3 Add link description instruction to `BUG_RESEARCHER_PROMPT`

## 5. Update orchestrator prompt

- [x] 5.1 Update `ORCHESTRATOR_PROMPT` to reflect enriched References block format with context sentences
- [x] 5.2 Remove all references to `follow_url`, `depth_exceeded`, `already_followed`
- [x] 5.3 Clearly document that depth/cycle/classification are handled transparently by `fetch_reference`

## 6. Update tests

- [x] 6.1 Update `test_tracker.py` for new data model: replace `current_depth`/`increment_depth` assertions with `followed_urls` dict format and `register_pending`/`get_depth_for` assertions
- [x] 6.2 Update `test_multi_agent.py` depth scenario tests: "Multiple URLs at same level exhaust depth budget" → assert siblings share same depth
- [x] 6.3 Add test for per-URL depth: verify 6 siblings at depth 1 all succeed
- [x] 6.4 Add test for chain nesting: verify depth increments correctly through root → sibling → child → grandchild
- [x] 6.5 Add tests for `extract_sentence_context` (URL in sentence, URL at start, preceding sentence, no-sentence fallback)
- [x] 6.6 Add test for `register_pending` → `get_depth_for` → `mark_followed` lifecycle
- [x] 6.7 Update existing `TestFetchReferenceInjection` tests if needed for new block format with context sentences

## 7. Clean up dead code

- [x] 7.1 Identify and comment out / remove `_pause_after_delegation_callback` and `_on_finish_callback` in `summarizer.py` (no longer driven by the Python-side pause-and-inject loop)
- [x] 7.2 Remove or deprecate `format_url_injection_message` in `summarizer.py` if no other callers exist

## 8. Verify

- [x] 8.1 Run `uv run ruff check .` — no new lint errors
- [x] 8.2 Run `uv run pytest -n auto` — all tests pass
- [x] 8.3 Manual run against a real Mattermost thread with multiple references — verify depth correctly allows 4+ siblings and that context sentences appear in the References block
