## MODIFIED Requirements

### Requirement: LLM-driven reference selection
The orchestrator SHALL decide which references to follow based on their relevance to the discussion, using the classified URL list injected automatically after each delegation — not by calling a classification tool.

The orchestrator (LLM):
- SHALL read the classified URL list from the injected message after each delegation
- SHALL evaluate each listed URL for relevance to the discussion
- SHALL call `follow_url(url)` once per URL it decides to follow; the system handles cycle detection and depth tracking atomically
- SHALL skip following references that are irrelevant
- SHALL NOT call `track_references(command="classify_text", ...)` — this command no longer exists

#### Scenario: Orchestrator reads injected list and follows relevant URL
- **WHEN** a delegation completes and an injected message lists a GitHub PR
- **THEN** the orchestrator evaluates whether the PR is central to the discussion
- **THEN** if relevant, it calls `track_references(command="follow_url", url="...")` and delegates to `github_researcher`
- **THEN** it does NOT call `track_references(command="classify_text", ...)`

#### Scenario: Orchestrator skips irrelevant reference
- **WHEN** the injected message lists a URL that is only a passing mention
- **THEN** the orchestrator MAY decide to skip calling `follow_url` for that URL
- **THEN** only relevant references are delegated

#### Scenario: Orchestrator avoids duplicate fetching
- **WHEN** the orchestrator calls `follow_url` for a URL already followed at a prior depth
- **THEN** `follow_url` returns `already_followed`
- **THEN** the orchestrator does NOT re-delegate to that URL

## REMOVED Requirements

### Requirement: URL classification for delegation routing (classify_text command)
**Reason**: URL classification now happens in the Python callback layer before results reach the LLM. The `classify_text` LLM tool command caused the LLM to echo the entire thread content (~40K tokens) into its action output, permanently inflating conversation context. The classification capability is preserved in Python via `classify_urls_in_text()`.
**Migration**: The orchestrator prompt no longer instructs the LLM to call `classify_text`. Classified URLs arrive automatically as an injected message after each delegation. Tests that exercised `classify_text` via the LLM tool should be replaced with tests that verify the injected message is present after delegation.
