# Spec: Mattermost Conversation Summarizer

## Capability

Summarize Mattermost conversation threads into structured output (TL;DR, narrative, action items) using an agentic AI approach.

## Requirements

### REQ-001: Permalink Input
The system SHALL accept a Mattermost permalink URL as input and extract the post ID from it.
- URL format: `https://{server}/{team}/pl/{post_id}`
- SHALL raise ValueError for invalid permalinks

### REQ-002: Thread Fetching
The system SHALL fetch the complete thread (root post + all replies) via Mattermost API v4.
- Endpoint: `GET /api/v4/posts/{post_id}/thread`
- SHALL sort replies chronologically
- SHALL auto-resolve user IDs to display names in v1

### REQ-003: User Resolution
The system SHALL resolve Mattermost user IDs to human-readable names.
- Endpoint: `GET /api/v4/users/{user_id}`
- v1: auto-resolve all users in FetchThread
- GetUserProfile tool SHALL remain available for agent-driven resolution

### REQ-004: Channel Context
The system SHALL provide channel context when available.
- Endpoint: `GET /api/v4/channels/{channel_id}`
- v1 nice-to-have: FetchChannel tool
- SHALL include channel name, purpose, and header in output

### REQ-005: Agent-based Summarization
The system SHALL use the OpenHands Software Agent SDK to perform summarization.
- Agent SHALL have access to FetchThread, GetUserProfile, FetchChannel, and finish tools
- Agent SHALL use a reasoning loop (not single-shot)
- Agent SHALL call the finish tool with structured output when satisfied

### REQ-006: Stop Condition
The system SHALL use the finish tool as the primary stop condition.
- FinishAction SHALL accept: tldr, narrative, action_items, participants
- StuckDetector SHALL be enabled as a safety net
- If stuck is detected, the system SHALL return a partial result or raise an error

### REQ-007: TL;DR Output
The system SHALL produce a bullet-point TL;DR (3-5 points) capturing key outcomes and decisions.

### REQ-008: Narrative Output
The system SHALL produce a chronological narrative appendix describing who said what and how the discussion evolved.

### REQ-009: Action Items
The system SHALL extract action items, decisions, and follow-ups mentioned in the thread.

### REQ-010: Participants
The system SHALL list all participants who contributed substantively to the thread.

### REQ-011: Metadata
The system SHALL include metadata at the bottom of the output: thread length, token stats, model used, duration.
- The `Tokens:` string SHALL be appended after `Duration` as the final metadata line.
- The system SHALL format the Tokens string exactly as: `Tokens: ↑ input {input} • cache hit {hit}% • reasoning {reasoning} • ↓ output {output} • $ {cost}`
- The `{cost}` SHALL be formatted to 2 decimal places (e.g., `0.00`).
- Token numbers `>= 1000` SHALL be divided by 1000, given two decimal places, and suffixed with `K` (e.g., `35.69K`). Token numbers `< 1000` SHALL be printed as exact integers.
- If `{hit}` evaluates to 0, the `cache hit` segment SHALL be omitted from the output.
- If `{reasoning}` evaluates to 0, the `reasoning` segment SHALL be omitted from the output.

#### Scenario: Metadata with cache hits and reasoning tokens
- **WHEN** the agent returns a summary with 35690 input tokens, 1000 cache read tokens, 653 reasoning tokens, 1820 output tokens, and 0.0042 cost
- **THEN** the metadata string includes `Tokens: ↑ input 35.69K • cache hit 2.73% • reasoning 653 • ↓ output 1.82K • $ 0.00` at the bottom.

#### Scenario: Metadata with zero reasoning and zero cache hit
- **WHEN** the agent returns a summary with 500 input tokens, 0 cache read tokens, 0 reasoning tokens, 500 output tokens, and 0.0001 cost
- **THEN** the metadata string includes `Tokens: ↑ input 500 • ↓ output 500 • $ 0.00` at the bottom.

### REQ-012: Configuration
The system SHALL support TOML as primary config source with env var override.
- TOML file path configurable (default: `mattermost-summarizer.toml`)
- Env var prefix: `MM_`
- Precedence: env var > TOML > defaults
- Required: mattermost_url, mattermost_token, llm_api_key
- Optional: llm_model (default: openai/gpt-4o), llm_base_url

### REQ-013: OpenAI-compatible LLM
The system SHALL support any OpenAI-compatible LLM provider via base_url configuration.
- Uses LiteLLM model naming convention (provider/model_name)
- base_url SHALL default to None (provider default)

### REQ-014: HTTP Client
The system SHALL use httpx (raw) for Mattermost API communication.
- Sync client (matching OpenHands tool execution model)
- Shared instance across tool executors for connection pooling
- Bearer token authentication

### REQ-015: Logging Separation
The system SHALL write all intermediate logs (from standard library logging, OpenHands SDK, or any internal processes) to a file, ensuring that the standard output (`stdout`) is exclusively used for the final output result of the application.

#### Scenario: Running CLI with stdout redirection
- **WHEN** the user runs the `summarize.py` CLI script and pipes the output
- **THEN** the piped `stdout` output contains only the `SummaryResult` string or JSON
- **THEN** a log file (e.g., `mattermost-summarizer.log`) is created or updated with intermediate agent and system logs

## Tool Roadmap

### v1 (MVP)
- FetchThread tool (with auto user resolution)
- GetUserProfile tool
- finish tool
- FetchChannel tool (nice-to-have)

### v2
- SearchPosts tool (cross-thread references)
- FetchFile tool (attachment content)
- GetTeam tool (team context)
- Paginated thread fetching (long thread support)
- Post summary back to Mattermost

### v3
- Multi-server support
- Real-time thread monitoring
- Custom prompt templates
- Output format options (markdown, JSON, HTML)

## API Surface

```python
# High-level API
summarizer = MattermostSummarizer.from_config("config.toml")
result = summarizer.summarize("https://chat.canonical.com/canonical/pl/abc123")

# Result access
result.tldr           # str: bullet-point summary
result.narrative      # str: chronological story
result.action_items    # list[str]: decisions/todos
result.participants    # list[str]: contributor names
result.metadata        # SummaryMeta
```

## Error Classes

| Error | When |
|-------|------|
| `PermalinkError` | Invalid URL format |
| `AuthenticationError` | 401 from Mattermost |
| `ThreadNotFoundError` | 404 from Mattermost |
| `AgentStuckError` | StuckDetector triggered, no finish produced |
| `LLMError` | LLM provider errors (wrapped from OpenHands) |
| `ConfigError` | Missing required config fields |
