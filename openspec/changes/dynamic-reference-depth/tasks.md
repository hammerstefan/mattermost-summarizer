## 1. Config Updates

- [ ] 1.1 Update `MattermostSummarizerConfig.max_reference_depth` in `src/mattermost_summarizer/config.py` to `int | None` and `default=None`.
- [ ] 1.2 Run `uv run mypy .` and `uv run ruff check .` to catch any immediate typing errors caused by the type change.
- [ ] 1.3 Update tests in `tests/test_config.py` (if any exist) to reflect that `max_reference_depth` defaults to `None`.

## 2. Summarizer Logic Updates

- [ ] 2.1 In `src/mattermost_summarizer/summarizer.py`, find the `summarize` method.
- [ ] 2.2 Add logic to determine `effective_depth`: if `self.config.max_reference_depth` is not None, use it. Otherwise, map the `level` argument (or `self.config.summarizer_default_level`) to `0` (brief), `1` (normal), or `3` (detailed).
- [ ] 2.3 Update the initialization of `ReferenceTracker(max_depth=effective_depth)` in `summarize` to use the dynamically calculated depth.
- [ ] 2.4 Verify typing matches with `uv run mypy .` and `uv run pyright`.

## 3. Testing and Verification

- [ ] 3.1 Update or add unit tests for `summarize()` to verify the `ReferenceTracker` receives the correct `max_depth` depending on `level` and explicit config values.
- [ ] 3.2 Run the full test suite `uv run pytest -n auto` to ensure no regressions.