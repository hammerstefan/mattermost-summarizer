## MODIFIED Requirements

### Requirement: Orchestrator coordination loop
The orchestrator agent SHALL follow a coordination loop driven by a Python depth loop in `summarizer.py`.

The Python depth loop:
1. Arms a `_pause_after_delegation_callback` that pauses `run()` on the first `DelegateObservation`
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
- **THEN** the `_pause_after_delegation_callback` does not fire a second time
- **THEN** `run()` continues to finish without further pausing
- **THEN** orchestrator synthesizes only the root thread content and calls finish

#### Scenario: Orchestrator completes after one recursion level
- **WHEN** the root thread references a Launchpad bug
- **THEN** Python pauses after thread_fetcher completes, injects the bug URL as a message
- **THEN** orchestrator calls `follow_url(bug_url)` → success; delegates to bug_researcher
- **THEN** Python pauses after bug_researcher completes; no further URLs found; no injection
- **THEN** `run()` continues to finish; orchestrator synthesizes and calls finish

#### Scenario: Pause fires exactly once per delegation
- **WHEN** the `_pause_after_delegation_callback` is armed for a depth segment
- **THEN** it fires on the first `DelegateObservation` in that segment
- **THEN** it does NOT fire again on subsequent events in the same segment
- **THEN** it is re-armed before the next `conv.run()` call

### Requirement: Orchestrator system prompt
The orchestrator agent's system prompt SHALL instruct the agent to:

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
