## MODIFIED Requirements

### Requirement: Orchestrator coordination loop
The orchestrator agent SHALL follow a coordination loop driven by the `FetchReferenceExecutor` and the enriched References block.

The loop:
1. The orchestrator receives a user message with the permalink URL
2. The orchestrator calls `fetch_reference(url=<permalink>)` — the `FetchReferenceExecutor` fetches the root thread via a `thread_fetcher` sub-agent
3. The observation returned includes the result text plus an optional "References found in result" block listing followable URLs with context sentences
4. The orchestrator evaluates each listed URL for relevance using the provided context sentence
5. For each relevant URL, the orchestrator calls `fetch_reference(url=<url>)`
6. Each call returns a result with (possibly) another References block
7. The orchestrator repeats steps 4-6 for any newly-surfaced references until no more References blocks appear, depth limit is reported reached, or all listed URLs judged irrelevant
8. The orchestrator synthesizes all gathered context and calls `finish`

The orchestrator SHALL NOT be responsible for tracking depth, cycles, or classification — the `FetchReferenceExecutor` handles these transparently in Python.

#### Scenario: Orchestrator completes without recursion
- **WHEN** the root thread result contains no References block
- **THEN** the orchestrator synthesizes only the root thread content and calls finish
- **THEN** no further `fetch_reference` calls are made

#### Scenario: Orchestrator completes after following relevant URLs
- **WHEN** the root thread result's References block lists a Launchpad bug URL with context "Bug tracks the root cause fix"
- **THEN** the orchestrator calls `fetch_reference` for the bug URL
- **THEN** the bug_researcher result contains no further References block
- **THEN** the orchestrator synthesizes and calls finish

#### Scenario: Orchestrator skips irrelevant references
- **WHEN** the References block lists a GitHub URL with context "Community bug report tangentially mentioned"
- **THEN** the orchestrator may judge it irrelevant and skip it
- **THEN** only references the orchestrator deems relevant are followed

#### Scenario: Orchestrator stops when depth limit reached
- **WHEN** the References block says "Maximum reference depth reached"
- **THEN** the orchestrator stops following references
- **THEN** the orchestrator synthesizes and calls finish

### Requirement: Orchestrator system prompt
The orchestrator agent's system prompt SHALL be provided via `AgentContext.system_message_suffix` and SHALL instruct the agent to:

- Parse the permalink from the user message
- Call `fetch_reference(url=<permalink>)` to fetch the root thread
- Read the result — if a "References found in result" block is present, evaluate each URL using the provided context sentence
- Call `fetch_reference(url=<url>)` for each relevant URL
- Repeat with each result until no more References blocks appear or "Maximum reference depth reached" is shown
- Synthesize gathered context into a coherent summary
- Call the finish tool with structured output

The prompt SHALL NOT instruct the agent to call `follow_url`, `classify_text`, `mark_followed`, or `track_references` — those commands no longer exist. Depth, cycle, and classification handling are automated by the `fetch_reference` tool.

#### Scenario: System prompt guides fetch_reference usage
- **WHEN** the orchestrator receives a result containing a References block
- **THEN** it calls `fetch_reference(url=<url>)` for each URL it judges relevant
- **THEN** on error responses (e.g. "Already followed", "Maximum depth reached", "Unsupported URL type"), it skips the URL and continues

#### Scenario: System prompt in user message vs system message
- **WHEN** the system prompt is configured via AgentContext.system_message_suffix
- **THEN** it is sent once as the system message (benefiting from provider caching)
- **THEN** user messages contain only task-specific input (permalink URL) and `fetch_reference` results
- **THEN** user messages do NOT include the full system prompt each turn

## REMOVED Requirements

### Requirement: Python depth loop in summarizer.py
**Reason**: The `_pause_after_delegation_callback`, `classify_urls_in_text` call, and `conv.send_message()` injection loop in `summarizer.py` were designed for the old `follow_url` / `delegate` model where Python paused conversation execution to classify and inject URLs between rounds. The new model moves classification and injection into `FetchReferenceExecutor.__call__`, which runs inside the tool executor during normal `fetch_reference` tool calls. The Python-side pause-and-inject loop is no longer needed — the orchestrator LLM receives enriched References blocks inline with each `fetch_reference` result.
**Migration**: The `_pause_after_delegation_callback` and `_on_finish_callback` logic in `summarizer.py`, and the `format_url_injection_message` function, are no longer used by the new code path. They may be removed immediately or kept as dead code (to be cleaned up later). The `build_reference_following_prompt` function in `reference_tracker.py` is updated to accept the new depth model but serves the same purpose of formatting the References block.
