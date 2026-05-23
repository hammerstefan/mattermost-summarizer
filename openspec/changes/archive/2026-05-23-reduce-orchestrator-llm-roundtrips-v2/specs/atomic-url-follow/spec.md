## ADDED Requirements

### Requirement: Atomic URL follow command
The `track_references` tool SHALL provide a `follow_url(url)` command that atomically checks followability, marks the URL as followed, and increments depth in a single operation.

The command SHALL return one of three outcomes:
- `success` — URL was not previously followed and depth limit not exceeded; URL is now marked followed and depth incremented
- `already_followed` — URL was already followed; no state change
- `depth_exceeded` — maximum depth reached; URL is not marked followed

The operation SHALL execute under the tracker lock to prevent TOCTOU races in concurrent delegation scenarios.

#### Scenario: follow_url succeeds for new URL within depth
- **WHEN** `follow_url` is called with a URL not previously followed and current depth < max_depth
- **THEN** the URL is marked as followed
- **THEN** the depth counter is incremented
- **THEN** the command returns `success`

#### Scenario: follow_url returns already_followed for duplicate
- **WHEN** `follow_url` is called with a URL that has already been followed
- **THEN** no state change occurs
- **THEN** the command returns `already_followed`

#### Scenario: follow_url returns depth_exceeded at max depth
- **WHEN** `follow_url` is called and current depth equals max_depth
- **THEN** the URL is NOT marked as followed
- **THEN** the depth counter is NOT incremented
- **THEN** the command returns `depth_exceeded`

#### Scenario: follow_url is atomic under concurrent calls
- **WHEN** two concurrent callers call `follow_url` with the same URL simultaneously
- **THEN** exactly one returns `success` and one returns `already_followed`
- **THEN** depth is incremented exactly once

#### Note: Depth counts total URLs followed, not recursion levels
`follow_url` increments depth once per successful call, regardless of how many URLs are followed at the same recursion level. This matches the existing 4-step protocol's behaviour and is intentional: `max_reference_depth` limits total context-gathering work, not nesting depth.

With `max_depth=3`, following 3 URLs at depth 0 will exhaust the depth budget after the third `follow_url` call, returning `depth_exceeded` for any further URLs.

If per-level semantics are desired in the future, `increment_depth` should be decoupled from `follow_url` and called once by the Python depth loop after all same-level delegations complete — but that is out of scope for this change.

## REMOVED Requirements

### Requirement: Individual bookkeeping commands
**Reason**: Replaced by the atomic `follow_url` command. The individual commands (`is_followed`, `can_follow`, `mark_followed`, `increment_depth`) required 4 LLM round-trips per URL with no LLM judgment between steps. The atomic command eliminates 3 round-trips per URL.
**Migration**: Replace all callers of the 4-step sequence with a single `follow_url(url)` call and branch on the returned outcome.

### Requirement: classify_text command
**Reason**: URL classification from bulk text is now performed by Python between `run()` segments in `summarizer.py`. Exposing it as an LLM tool caused the LLM to echo ~44K chars of thread content verbatim as a tool argument, permanently inflating the conversation context.
**Migration**: URL classification happens automatically; the orchestrator receives classified URLs as an injected user message after each delegation. No LLM action required.
