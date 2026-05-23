## MODIFIED Requirements

### Requirement: Orchestrator system prompt
The orchestrator agent's system prompt SHALL be provided via AgentContext.system_message_suffix and SHALL instruct the agent to:

- Parse the permalink from the user message
- Delegate to appropriate sub-agents for the root thread
- Read the classified URL list from the automatically injected message after each delegation to identify URLs with their types and target sub-agents
- Decide which references to follow based on relevance (LLM-driven selection)
- Call `track_references(command="follow_url", url="...")` before delegating for a chosen URL
- Track recursion depth and stop at max_depth
- Synthesize gathered context into a coherent summary
- Call the finish tool with structured output
- NOT call `track_references(command="classify_text", ...)` — URL classification is automatic
- NOT call `track_references(command="is_followed", ...)`, `can_follow`, `mark_followed`, or `increment_depth` — these commands no longer exist; use `follow_url` instead

#### Scenario: System prompt in user message vs system message
- **WHEN** the system prompt is configured via AgentContext.system_message_suffix
- **THEN** it is sent once as the system message (benefiting from provider caching)
- **THEN** user messages contain only task-specific input (permalink URL)
- **THEN** user messages do NOT include the full system prompt each turn

#### Scenario: Orchestrator uses injected URL list instead of classify_text
- **WHEN** the orchestrator receives a delegation observation
- **THEN** it reads the classified URL list from the subsequent injected message
- **THEN** it does NOT call `track_references(command="classify_text", ...)`
- **THEN** it decides which URLs to follow based on relevance and calls `follow_url` for each chosen URL
