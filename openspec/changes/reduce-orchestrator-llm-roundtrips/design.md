## Context

The orchestrator agent uses a `track_references` tool to manage URL bookkeeping during recursive reference following. Two distinct inefficiencies exist:

1. **Classification overhead**: `classify_text` is called by the LLM to extract URLs from 44K-char thread content. This is pure regex work with no LLM judgment. Worse, the tool argument contains the full thread text, which the LLM echoes verbatim into its action output (~40K tokens), permanently inflating context from ~10K to 693K tokens over a session.

2. **Bookkeeping overhead**: 4 LLM round-trips per URL (`is_followed` → `can_follow` → `mark_followed` → `increment_depth`) despite the underlying operations being pure Python state mutation with no LLM judgment between steps. With 3 URLs followed, this is 12 wasted round-trips (~141s) plus 2 `classify_text` calls (~41s) = ~182s of 571s total (32%).

The `DelegateTool` is a generic thin wrapper and must not acquire domain-specific logic.

## Goals / Non-Goals

**Goals:**
- Remove `classify_text` from the LLM tool surface entirely; move classification to a Python callback
- Automatically inject a classified URL list into the conversation after each delegation
- Replace the 4-step per-URL bookkeeping sequence with a single atomic `follow_url` command
- Keep `DelegateTool` unchanged

**Non-Goals:**
- Removing the LLM's ability to decide *which* URLs to follow (relevance is genuine LLM work)
- Changing the `ReferenceTracker` Python class itself
- Altering sub-agent registration or the `DelegateTool` interface

## Decisions

### Decision 1: Post-delegation callback injects classified URL list as synthetic message

**Choice**: In `summarizer.py`, alongside the existing `_on_finish_callback`, register a `_post_delegation_callback` closure that:
1. Guards with `isinstance(obs, DelegateObservation)` — fires only on delegation events
2. Calls `classify_urls_in_text(obs_text, tracker)` in Python
3. If URLs found, calls `conv_ref[0].send_message(...)` with the formatted list

**Rationale**: Fully outside `DelegateTool`. Uses the same callback mechanism already present for `_on_finish_callback`. `ReferenceTracker` instance is captured in the closure — no IPC needed. `send_message` is confirmed safe to call from callbacks during `run()` (see SDK safety analysis below).

**Alternatives considered**:
- Subclass `DelegateExecutor` and append URL block to observation text (prior design in `pre-extract-urls-before-agent-loop`): appends to the observation that is already in context — the 40K observation stays. The callback approach instead puts classification into a *separate* message, keeping the observation and the URL list distinct and independently skimmable by the LLM.
- `PostToolUse` hook (shell command): out-of-process, cannot share in-memory `ReferenceTracker` state without IPC.
- `user_message_suffix` on `AgentContext`: static field, cannot update dynamically per delegation turn.

**Message format**:
```
References found in delegation result:
1. https://github.com/o/r/pull/6843  (github_pr → github_researcher)
2. https://bugs.launchpad.net/ubuntu/+bug/2098515  (launchpad_bug → bug_researcher)
Depth: 1/3 — can follow more

Decide which (if any) are relevant and call follow_url before delegating.
```

If no followable URLs found: no message is injected.

### Decision 2: Atomic `follow_url` command replaces 4-step sequence

**Choice**: Add a `follow_url(url)` command to `ReferenceTrackingExecutor` that atomically runs `has_been_followed` check, `can_follow_deeper` check, `mark_followed`, and `increment_depth` under `tracker.lock()`, returning one of three outcomes: success, already-followed, or depth-exceeded.

**Rationale**: The 4-step sequence exists because the LLM was designed to call each step individually, but there is no LLM judgment between steps — it always runs all 4 unconditionally. Collapsing them saves 3 round-trips per URL (9 round-trips saved for a typical 3-URL run).

**Alternatives considered**:
- Keep 4 steps, cache at SDK layer — SDK has no per-tool result cache; would require patching SDK internals.
- Move all tracking to pre/post hooks — hooks are out-of-process shell commands, IPC required.

The `classify_text`, `is_followed`, `can_follow`, `mark_followed`, and `increment_depth` commands are removed from the tool description and executor. `classify` (single URL) and `reset` are retained.

### Decision 3: Orchestrator prompt updated to reflect new interface

The `ORCHESTRATOR_PROMPT` in `agent.py` is updated to:
- Remove all `classify_text` instructions
- Replace the 4-step per-URL protocol with a single `follow_url(url)` call
- Note that classified URLs are provided automatically as a message after each delegation

### SDK safety: `send_message` during `run()` is safe

Investigated `local_conversation.py`, `fifo_lock.py`, and `state.py`:

- `ConversationState` is guarded by a `FIFOLock` — a reentrant, FIFO-fair lock (`sdk/conversation/fifo_lock.py`)
- Callbacks fire inside `run()`'s `with self._state:` block on the same thread; reentrancy applies — no deadlock
- `send_message` enqueues a `MessageEvent` via `_on_event`; `run()` processes it on the next `agent.step()` iteration
- This is explicitly the designed behaviour: `local_conversation.py:610` documents concurrent `send_message` during `run()` as an intentional use case
- Constraint: callback must not block before calling `send_message`. `classify_urls_in_text` is pure regex (microseconds) — constraint satisfied.

## Risks / Trade-offs

**[Risk] Callback fires on every event** → Mitigation: guard with `isinstance(obs, DelegateObservation)`; no-op check costs nanoseconds.

**[Risk] Removing individual commands breaks existing tests** → Mitigation: update affected tests in the same PR.

**[Risk] Injected classification message slightly increases token count** → Trade-off accepted: one ~200-token message per delegation is negligible against the ~182s / ~3.3M token saving.

**[Risk] `DelegateObservation` attribute name for result text changes in SDK** → Mitigation: confirm attribute during implementation (`to_llm_content` or `.content`); add a defensive check with a clear error if missing.

## Migration Plan

1. Add `follow_url` to `ReferenceTrackingExecutor`; remove deprecated commands
2. Add `_post_delegation_callback` to `summarizer.py`; pass in `callbacks` list
3. Update `ORCHESTRATOR_PROMPT` in `agent.py`
4. Update tests
5. No config changes; no new dependencies; no migration needed for existing deployments
