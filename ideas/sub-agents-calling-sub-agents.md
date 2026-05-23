# Idea: Sub-agents calling sub-agents for recursive reference discovery

## Status
Idea — not pursued. Documented as an alternative to Option C (depth parameter on `FetchReferenceAction`).

## Context

Discovered during analysis of MLflow trace `tr-db8d5690dc754485677cf727c9a058ca` (May 2026).

The orchestrator currently:
1. Fetches the root Mattermost thread via `fetch_reference`
2. Receives a References block listing followable URLs found in the result
3. Decides which URLs to follow and calls `fetch_reference` for each
4. Synthesizes all results into a final summary

This creates two problems:
- **Depth counting is wrong**: each sibling fetch burns a depth slot, so with `max_depth=3` the 4th reference from the root thread is blocked even though no nesting has occurred at all (see `fetch_reference_tool.py` `increment_depth` logic)
- **Relevance decisions are uninformed**: the orchestrator only sees a bare URL + type label and has to guess relevance from the URL path and prose mentions in the sub-agent's summary. The sub-agent that actually read the content is far better positioned to judge relevance.

## The idea

Instead of the orchestrator looping over a References block, give sub-agents access to `fetch_reference` and let them recursively fetch relevant URLs themselves. Recursion depth maps naturally to call stack depth.

### What the flow would look like

```
orchestrator
  └─ fetch_reference(root_thread)          ← orchestrator makes ONE call
       └─ thread_fetcher sub-agent
            ├─ fetch_thread(root)           ← sees GitHub/LP URLs in content
            ├─ fetch_reference(issues/6867) ← sub-agent decides this is the filed bug
            │    └─ github_researcher
            │         ├─ fetch_github_issue(6867)
            │         └─ finish("Issue #6867: ...")
            ├─ fetch_reference(pull/6868)   ← sub-agent decides this is the proposed fix
            │    └─ github_researcher
            │         └─ ...
            └─ finish(combined summary of thread + all fetched refs)
```

The orchestrator's job becomes: call `fetch_reference(root_url)`, get back a fully-enriched summary, call `finish`. One orchestrator LLM roundtrip total.

### Why it's appealing

- **Depth naturally maps to call stack depth** — no explicit counter or shared mutable state needed
- **Relevance decisions made by the right agent** — the `thread_fetcher` that read the thread knows which URLs are the "proposed fix" vs "tangentially mentioned"
- **Orchestrator becomes trivially simple** — one `fetch_reference` call, one `finish` call
- **No LLM roundtrip per reference at the orchestrator level**

### Implementation sketch

1. `create_thread_fetcher()` in `subagents/__init__.py` gains `fetch_reference` in its tool list, wired to the shared `ReferenceTracker`
2. `THREAD_FETCHER_PROMPT` updated to instruct the sub-agent to call `fetch_reference` for URLs it judges relevant (proposed fixes, blockers, root cause bugs) rather than just listing them
3. `github_researcher` and `bug_researcher` similarly get `fetch_reference` if their results might contain further relevant links
4. Depth tracking: each sub-agent call to `fetch_reference` passes the current nesting depth; the tracker checks `depth < max_depth` (same as Option C but called from sub-agents)
5. The References block injection in `FetchReferenceExecutor` may still be useful as a fallback / for the orchestrator-level call, but sub-agents bypass it by calling `fetch_reference` directly

### Why it was not pursued (at time of writing)

1. **Conflicts with the planned architectural flattening** (`TODOS.md`: "Remove LLM Sub-Agents for Pure Data Fetching — give fetching tools directly to the Orchestrator"). This idea goes in the opposite direction.

2. **Depth tracking bug is the same** — `ReferenceTracker.current_depth` has the sibling-counting problem regardless of who calls `fetch_reference`. The depth-as-parameter fix (Option C) is still needed.

3. **Shared tracker wiring is non-trivial** — sub-agent factories currently receive an LLM and a Mattermost client. Injecting a shared `ReferenceTracker` into `thread_fetcher`, `github_researcher`, and `bug_researcher` requires plumbing changes through `register_subagents()`, `build_orchestrator_agent()`, and the `FetchReferenceTool.create()` call chain.

4. **Harder to debug** — recursion buried 3-4 `conversation → agent.step` levels deep. The tracing patch helps, but reasoning about what happened in a failed run is significantly harder.

5. **Sub-agent LLM also has to judge relevance** — adds a second responsibility to sub-agents that were designed as single-purpose fetchers. A sub-agent that over-follows can trigger cascading fetches that are difficult to bound.

6. **Sequential by default** — a sub-agent fetches references one at a time inside its `conversation.run` loop. The orchestrator model allows parallel `fetch_reference` calls in a single LLM turn (exploiting native parallel tool calling, also in `TODOS.md`).

## Relationship to Option C (depth parameter)

Option C fixes depth tracking by carrying `depth` as a field on `FetchReferenceAction` (so sibling fetches all carry `depth=1` rather than incrementing a shared counter). It also proposes enriching the References block with surrounding context sentences so the orchestrator can make better relevance decisions.

This idea and Option C are mutually exclusive at the architectural level:
- Option C keeps the orchestrator as the decision-maker and fixes its information deficit via enriched context
- This idea moves the decision-maker down to the sub-agents

## Recommended trigger to revisit

Revisit if:
- The enriched-context approach in Option C still produces poor relevance decisions after a few test runs
- The architectural flattening plan is abandoned or delayed significantly
- A test with a complex thread shows the orchestrator consistently missing important references that a content-aware sub-agent would have caught
