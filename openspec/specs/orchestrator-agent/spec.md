# Spec: Orchestrator Agent

## Capability

Coordinate sub-agents via DelegateTool to gather context recursively and produce summaries using an orchestrator agent architecture with level-specific finish tools.

## Requirements

### Requirement: Orchestrator agent architecture
The system SHALL use an orchestrator agent that coordinates sub-agents via DelegateTool to gather context and produce summaries.

The orchestrator agent:
- SHALL have access to DelegateTool and a level-specific finish tool
- SHALL NOT have access to data-fetching tools (FetchThread, FetchLaunchpadBug, etc.)
- SHALL use AgentContext with system_message_suffix for the system prompt
- SHALL delegate all data fetching to appropriate sub-agents

#### Scenario: Orchestrator delegates thread fetch
- **WHEN** the orchestrator receives a permalink to summarize
- **THEN** it delegates to a thread_fetcher sub-agent
- **THEN** it waits for the consolidated delegation result
- **THEN** it scans the returned text for references

#### Scenario: Orchestrator uses level-specific finish tool
- **WHEN** the orchestrator produces a summary
- **THEN** it calls the finish tool matching the requested summarization level (brief, normal, or detailed)

### Requirement: Orchestrator coordination loop
The orchestrator agent SHALL follow a coordination loop driven by a Python depth loop in `summarizer.py`.

The Python depth loop:
1. Arms a `_pause_after_delegation_callback` that pauses `run()` on the first `delegate`-command `DelegateObservation` (guarded by `isinstance(event, ObservationEvent) and isinstance(event.observation, DelegateObservation) and event.observation.command == "delegate"`; excludes spawn observations)
2. Calls `conv.run()` — runs until the first delegation completes, then pauses
3. Extracts delegation result text from `conversation.state.events`
4. Calls `classify_urls_in_text(text, tracker)` in Python
5. If followable URLs found: injects a classified URL list via `conv.send_message()`
6. Re-arms the callback and calls `conv.run()` again
7. Repeats until finish observed, depth exhausted, or no new followable URLs

The orchestrator LLM:
1. Parses user input (permalink URL)
2. Delegates to thread_fetcher for the root thread
3. Receives classified URL list as an injected user message (if any URLs found)
4. Evaluates each URL for relevance
5. For each relevant URL: calls `follow_url(url)` then delegates to the indicated sub-agent
6. Repeats steps 3-5 until no further URLs or depth exceeded
7. Synthesizes all gathered context
8. Calls finish with structured summary

#### Scenario: Orchestrator completes without recursion
- **WHEN** the root thread has no referenced URLs
- **THEN** Python does not inject any URL message after the initial delegation
- **THEN** `run()` continues to finish without further pausing (the callback's fired-flag prevents re-firing)
- **THEN** orchestrator synthesizes only the root thread content and calls finish

#### Scenario: Orchestrator completes after following one URL
- **WHEN** the root thread references a Launchpad bug
- **THEN** Python pauses after thread_fetcher completes, injects the bug URL as a message
- **THEN** orchestrator calls `follow_url(bug_url)` → success; delegates to bug_researcher
- **THEN** Python pauses after bug_researcher completes; no further URLs found; no injection
- **THEN** `run()` continues to finish; orchestrator synthesizes and calls finish

#### Scenario: Pause fires exactly once per delegation
- **WHEN** the `_pause_after_delegation_callback` is armed for a depth segment
- **THEN** it fires only on `ObservationEvent` events where `event.observation` is a `DelegateObservation` with `event.observation.command == "delegate"`
- **THEN** it does NOT fire on spawn observations (`command == "spawn"`) — those would cause a spurious pause+run cycle after every agent spawn
- **THEN** it does NOT fire on action events or any other event types
- **THEN** it does NOT fire again on subsequent events in the same segment (fired-flag is set after first fire)
- **THEN** the fired-flag is reset before each subsequent `conv.run()` call to re-arm the callback

#### Scenario: Orchestrator judges injected URLs as irrelevant and finishes directly
- **WHEN** Python injects a classified URL list after a delegation
- **AND** the orchestrator LLM judges all listed URLs as irrelevant to the discussion
- **THEN** the orchestrator calls no `follow_url` and no further `delegate`
- **THEN** the orchestrator calls `finish` with a summary drawn from gathered context
- **THEN** the `_on_finish_callback` fires, `conv.pause()` is called, and the depth loop exits normally
- **THEN** no `follow_url` or `depth_exceeded` outcomes are recorded

### Requirement: Orchestrator system prompt
The orchestrator agent's system prompt SHALL be provided via AgentContext.system_message_suffix and SHALL instruct the agent to:

- Parse the permalink from the user message
- Delegate to appropriate sub-agents for the root thread
- Expect classified URL lists to arrive as injected user messages after each delegation (not via tool calls)
- Decide which references to follow based on relevance
- Call `follow_url(url)` before each delegation to a referenced URL; branch on the outcome
- Synthesize gathered context into a coherent summary
- Call the finish tool with structured output

The prompt SHALL NOT instruct the agent to call `classify_text` — that command no longer exists.
The prompt SHALL NOT describe the 4-step bookkeeping sequence — it is replaced by `follow_url`.

#### Scenario: System prompt guides follow_url usage
- **WHEN** the orchestrator receives an injected classified URL list
- **THEN** it calls `follow_url(url)` for each URL it judges relevant
- **THEN** on `success`: delegates to the indicated sub-agent
- **THEN** on `already_followed` or `depth_exceeded`: skips the URL

#### Scenario: System prompt in user message vs system message
- **WHEN** the system prompt is configured via AgentContext.system_message_suffix
- **THEN** it is sent once as the system message (benefiting from provider caching)
- **THEN** user messages contain only task-specific input (permalink URL and injected URL lists)
- **THEN** user messages do NOT include the full system prompt each turn