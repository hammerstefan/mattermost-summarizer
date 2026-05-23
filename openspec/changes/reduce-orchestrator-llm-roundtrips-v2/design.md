## Context

The orchestrator agent runs inside a single `LocalConversation.run()` call. All 21 orchestrator steps — including URL classification and per-URL bookkeeping — execute as LLM-driven tool calls within that loop. Two categories of pure-Python work are unnecessarily exposed as LLM tools:

1. **`classify_text`**: extracts URLs from the 44K-char thread text using regex. The LLM echoes the full text as a tool argument, permanently inflating the conversation context from ~10K to ~693K tokens and consuming ~3.3M input tokens per run. Cost: ~2 round-trips and massive context bloat.

2. **4-step bookkeeping per URL** (`is_followed` → `can_follow` → `mark_followed` → `increment_depth`): 12 LLM round-trips for 3 URLs with zero LLM judgment between steps. Cost: ~141s of 571s total wall time.

### Why not callback injection?

A prior design registered a `_post_delegation_callback` on `LocalConversation` that would fire inside `run()`, call `classify_urls_in_text()` in Python, and inject the result as a synthetic `send_message`. SDK analysis confirmed this is technically safe (FIFOLock is reentrant; `send_message` enqueues on next `agent.step()`).

However, all production-like SDK examples perform Python enrichment *before* `run()`, never inside callbacks. The dominant idiom is: Python pre-processes → `run()` → Python post-processes → `run()` again. The callback approach is novel, undocumented, and harder to reason about. The sequential-runs pattern is idiomatic and already demonstrated by the existing `_on_finish_callback` / `pause()` mechanism.

## Goals / Non-Goals

**Goals:**
- Remove `classify_text` from the LLM tool surface; move URL classification to Python between `run()` segments
- Replace the 4-step per-URL bookkeeping sequence with a single atomic `follow_url` command
- Adopt the sequential-runs pattern: Python drives a depth loop, calling `run()`, pausing, enriching, and re-entering
- Keep `DelegateTool` unchanged
- Keep the LLM's relevance judgment (which URLs to follow) and task-string authoring (focused delegation instructions) intact

**Non-Goals:**
- Removing `delegate` — the sub-agent distillation and focused task strings are genuine value
- Changing `ReferenceTracker` Python internals
- Changing sub-agent registration or any sub-agent
- Altering the `LocalConversation` SDK

## Decisions

### Decision 1: Python depth loop with pause-after-delegation

**Choice**: In `summarizer.py`, replace the single `run()` call with a depth loop driven by a `_pause_after_delegation_callback`. At each depth:

1. Register a callback that calls `conv.pause()` on the first `DelegateObservation` received
2. Call `conv.run()` — it runs until the first delegation completes, then pauses
3. Python extracts the `DelegateObservation` text from `conversation.state.events`
4. Python calls `classify_urls_in_text(text, tracker)` — pure regex, microseconds
5. If followable URLs found, Python formats a compact classified list and calls `conv.send_message(...)` to inject it as the next user message
6. Python clears the pause-after-delegation callback (or re-arms for the next depth)
7. Python calls `conv.run()` again — the orchestrator LLM sees the injected URL list, makes relevance decisions, calls `follow_url` for chosen URLs, then calls `delegate` again
8. Loop repeats until depth exhausted, no new followable URLs, or `finish` observed

The `_on_finish_callback` already uses `pause()` to stop after finish — that mechanism is unchanged.

**Injected message format**:
```
References found in delegation result:
1. https://github.com/o/r/pull/6843  (github_pr → github_researcher)
2. https://bugs.launchpad.net/ubuntu/+bug/2098515  (launchpad_bug → bug_researcher)
Depth: 1/3 — can follow more

Decide which (if any) are relevant and call follow_url before delegating.
```

If no followable URLs found: no message is injected and `run()` continues without pausing.

**Rationale**: Uses the exact same `pause()` mechanism already present for `_on_finish_callback`. Python enrichment happens between `run()` segments — the idiomatic SDK pattern. No SDK internals touched. Callback is only armed when a delegation is expected; it disarms itself after firing once (or when finish is seen).

**Alternatives considered**:
- Callback injection mid-run (prior design): confirmed SDK-safe but novel and undocumented; rejected in favour of idiomatic sequential-runs pattern
- Pre-computing all URLs before any `run()`: cannot work — the orchestrator's task string for sub-agent delegation is written by the LLM based on context it has built; Python doesn't know what to ask for before the LLM decides

### Decision 2: Atomic `follow_url` command

**Choice**: Add `follow_url(url)` to `ReferenceTrackingExecutor` that atomically executes under `tracker.lock()`:
1. `has_been_followed(url)` — if true, return `already_followed`
2. `can_follow_deeper()` — if false, return `depth_exceeded`
3. `mark_followed(url)`
4. `increment_depth()`

Returns one of three outcomes: `success | already_followed | depth_exceeded`.

Remove `is_followed`, `can_follow`, `mark_followed`, `increment_depth` from executor and tool description. Retain `classify` (single-URL classification, still useful for the LLM to confirm routing before delegation) and `reset`.

**Rationale**: Saves 3 round-trips per URL (9 for a typical 3-URL run). No LLM judgment occurs between the 4 steps — they always run unconditionally. Atomicity under lock also removes a latent TOCTOU race in parallel delegation scenarios.

**Tool description after change**:
```
Commands:
  follow_url - Atomically check, mark, and register a URL as followed.
               Returns: success | already_followed | depth_exceeded
               (param: url)
  classify   - Classify a single URL to get its type and target sub-agent.
               (param: url)
  reset      - Reset tracker state for a new summary operation.
```

### Decision 3: Orchestrator prompt update

Remove all `classify_text` instructions. Replace the 4-step protocol section with:

```
After each delegation, you will receive a message listing references found in the result,
formatted as:
  References found in delegation result:
  1. <url>  (<type> → <sub-agent>)
  Depth: N/M — can follow more

For each reference you judge as relevant:
  1. Call follow_url(url) — returns success, already_followed, or depth_exceeded
  2. If success: delegate to the indicated sub-agent with a focused task
  3. If already_followed or depth_exceeded: skip

If no references message is injected, there are no followable URLs — proceed to synthesize.
```

### SDK mechanics

The `pause()` method sets `execution_status = PAUSED`, which causes `run()` to break at the top of its next iteration (checked under lock). `send_message()` enqueues a `MessageEvent`; on the next `run()` call, `_ensure_agent_ready()` re-validates state, then the loop immediately processes the queued message on the first `agent.step()`. This is exactly how the existing `_on_finish_callback` + `send_message` pattern works today.

The `_pause_after_delegation_callback` is a closure that:
- Guards with `isinstance(obs, DelegateObservation)` — no-op on every other event
- On first fire: calls `conv.pause()`, then sets a flag so it doesn't fire again in the same depth segment

## Risks / Trade-offs

**[Risk] `run()` may not pause between steps if delegation and a subsequent tool call are batched in one agent step** → Mitigation: the SDK processes one action per step; `DelegateAction` produces `DelegateObservation` as its own step. The pause fires on the observation event, which is processed before the next step begins.

**[Risk] Orchestrator LLM ignores injected URL list and calls `classify_text` anyway** → Mitigation: `classify_text` is removed from the tool surface. The LLM cannot call a tool that doesn't exist. Prompt update makes the new flow explicit.

**[Risk] Removing individual commands breaks existing tests** → Mitigation: update affected tests in the same PR.

**[Risk] `DelegateObservation` content attribute changes in a future SDK update** → Mitigation: access `obs.to_llm_content` or `obs.content`; add a defensive check with a clear error if missing. Use the same attribute access pattern already present in `_extract_finish_action`.

**[Risk] Injected classification message slightly increases token count per depth** → Accepted trade-off: one ~200-token message per depth level is negligible against the ~182s / ~3.3M token saving.

**[Trade-off] Depth loop adds complexity to `summarizer.py`** → The loop is straightforward (while not done: run, pause, classify, inject, run). The complexity is local to one function and well-motivated by performance data.
