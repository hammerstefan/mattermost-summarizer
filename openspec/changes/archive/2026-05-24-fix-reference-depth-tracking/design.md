## Context

The `ReferenceTracker` uses a single `current_depth: int` counter that increments on every non-root `fetch_reference` call. This means sibling references found in the same thread compete for depth slots — with `max_depth=3`, the 4th sibling URL is blocked before any nesting occurs. The orchestrator's References block shows bare URLs with no context, forcing the orchestrator LLM to guess relevance from URL paths alone.

The fix replaces the global counter with per-URL depth registration and enriches the References block with surrounding sentence context from the sub-agent result.

## Goals / Non-Goals

**Goals:**
- Depth correctly models nesting level, not total fetch count — siblings at the same level share the same depth
- With `max_depth=3`, you can follow e.g. 6 sibling references at depth 1, each surfacing sub-references at depth 2
- The orchestrator receives one sentence of context per URL in the References block
- No LLM involvement in depth tracking — depth is derived entirely in Python from the tracker

**Non-Goals:**
- Reducing LLM roundtrips per reference (deferred to `TODOS.md` flattening)
- Parallel reference fetching (deferred to `TODOS.md`)
- Sub-agents calling sub-agents for recursive discovery (documented in `ideas/sub-agents-calling-sub-agents.md`)

## Decisions

### 1. Replace `followed_urls: set[str]` and `current_depth: int` with `followed_urls: dict[str, int]` and `pending_urls: dict[str, int]`

**Rationale:** `dict[str, int]` is a strict superset of `set[str]` for cycle detection (`url in d` works identically). `pending_urls` stores URLs surfaced in the most recent References block with their correct child depth, so the next `fetch_reference(url)` call can look up `pending_urls.get(url)` to determine the depth to record at. After the URL is fetched (via `mark_followed`), it moves from `pending` to `followed`. Both `current_depth` and `increment_depth()` are removed.

**Alternatives considered:**
- Separate `set` + `dict`: More structs, no benefit — `dict` alone handles both cycle detection and depth lookup.
- Depth on `FetchReferenceAction`: Rejected in grilling — moving depth into the action makes the LLM responsible for copying it correctly, a reliability risk.

### 2. Pre-register pending URLs at injection time

When `FetchReferenceExecutor.__call__` finishes a sub-agent delegation and builds the References block (`build_reference_following_prompt`), it also calls `tracker.register_pending(url, depth=parent_depth + 1)` for each URL in the block. On the next `fetch_reference(url=...)` call, the executor looks up `tracker.get_pending_depth(url)` to know what depth to record the URL at when calling `mark_followed`.

**Rationale:** The injection moment is the only point where the executor knows both "this result was fetched at depth N" and "these are the URLs discovered inside it." Registration at injection time couples depth assignment to the source of discovery, not the call site.

**Fallback for root (unregistered) URLs:** The root URL has no pending entry (it was never surfaced in a References block). The executor treats `get_pending_depth(url) == None` as depth 0.

### 3. Depth limit check: `get_depth_for(url) < max_depth`

Before the executor delegates to a sub-agent, it checks the URL's assigned depth against `max_depth`. For the root URL (no registration → depth 0), this always passes. For registered URLs, it checks the pending depth — which is already `parent_depth + 1` and therefore correctly reflects the nesting level.

**Rationale:** The check is a simple comparison, not a shared mutable counter. No race conditions with sibling fetches because each URL's depth is pre-determined at registration.

### 4. Extract surrounding sentence for context enrichment

After sub-agent completion, `FetchReferenceExecutor` extracts the sentence containing (or immediately adjacent to) each URL from the result text. The sentence is appended to the URL's entry in the References block. A new helper `extract_sentence_context(text: str, url: str) -> str` is added to `reference_tracker.py`.

**Rationale:** The sub-agent already writes prose about each URL in its summary. Extracting the sentence costs nothing and gives the orchestrator a one-line description per reference instead of a bare URL. The sub-agent prompts are also updated to instruct explicit descriptive text near each URL.

**Alternatives considered:**
- Fixed character window: Produces truncated / mid-word text; less reliable than sentence boundaries.
- Sub-agent annotation format: Requires a parsing contract between sub-agent output and executor; adds fragility.
- No context extraction: Leaves the orchestrator guessing, which is the current broken behaviour.

### 5. Sub-agent prompt updates

`THREAD_FETCHER_PROMPT`, `GITHUB_RESEARCHER_PROMPT`, and `BUG_RESEARCHER_PROMPT` each gain:

> When listing or mentioning any URLs or references in your summary, always include a one-sentence description of what the link is and why it matters — write it immediately before or after the URL.

**Rationale:** The sentence extraction depends on good prose around URLs. This instruction makes the extracted context reliably informative.

## Risks / Trade-offs

- **[Risk] Sentence extraction may pick up the wrong sentence** if a URL appears in a context-switching paragraph. → **Mitigation:** The extractor takes the previous sentence if the URL is in the middle of a sentence, or the containing sentence if the URL starts one. Fallback: if no sentence boundary is within 300 chars, return `"(no description available)"`.
- **[Risk] `pending_urls` may leak between conversations** if the tracker is reused without reset. → **Mitigation:** The existing `reset()` method (called per-summary-operation) clears both `followed_urls` and `pending_urls`.
- **[Risk] Enriched context adds tokens to the orchestrator prompt.** → **Mitigation:** One sentence per URL is negligible compared to the 43k-char thread content the orchestrator already receives. If this becomes a concern, a max-context-length parameter can be added later.
- **[Risk] `build_reference_following_prompt` signature changes** (now needs parent depth). → **Mitigation:** The function already exists and is only called from `FetchReferenceExecutor`. The signature change is internal.

## Open Questions

- Should `get_depth_for(url)` return the registered depth for already-followed URLs (for diagnostic purposes), or only for pending/unregistered URLs? Decision: return for both — `followed_urls` holds depth after fetching, useful for trace introspection.
