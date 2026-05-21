# Tasks: Mattermost Conversation Summarizer

## v1 Implementation Tasks

### Project Setup

- [x] Create package directory structure under `src/mattermost_summarizer/`
- [x] Create `pyproject.toml` with dependencies: openhands-sdk, httpx, pydantic, pydantic-settings, tomli
- [x] Add ruff and mypy/pyright to dev dependencies
- [x] Create `__init__.py` with package exports

### Config Module

- [x] Create `config.py` with `MattermostSummarizerConfig` (pydantic-settings, TOML + MM_ env prefix)
- [x] Support `from_config(path: Path)` and `from_env()` classmethods
- [x] Required fields: mattermost_url, mattermost_token, llm_api_key
- [x] Optional fields: llm_model (default: openai/gpt-4o), llm_base_url (default: None)

### Data Models

- [x] Create `models.py` with PostData, PostThread, UserProfile, Channel, SummaryMeta, SummaryResult
- [x] Implement PostData with author_username auto-resolution logic
- [x] Implement SummaryResult.__str__() for pretty printing

### HTTP Client

- [x] Create `client.py` with MattermostClient class
- [x] Sync httpx.Client with base_url = f"{url}/api/v4"
- [x] Bearer token auth header
- [x] Implement get_post_thread(post_id) → PostThread
- [x] Implement get_user(user_id) → UserProfile
- [x] Implement get_channel(channel_id) → Channel
- [x] Implement close() method

### Permalink Parser

- [x] Create `utils.py` with parse_permalink(url: str) → str
- [x] Regex match `/pl/([a-z0-9]+)` against URL
- [x] Raise ValueError for invalid permalinks

### Tool: FetchThread

- [x] Create `tools/fetch_thread/definition.py`
- [x] Define FetchThreadAction (post_id: str) and FetchThreadObservation
- [x] Implement to_llm_content() with human-readable thread format
- [x] Create `tools/fetch_thread/impl.py` with FetchThreadExecutor
- [x] Auto-resolve user IDs to usernames in to_llm_content
- [x] Create `tools/fetch_thread/__init__.py` exporting FetchThreadTool

### Tool: GetUserProfile

- [x] Create `tools/get_user/definition.py`
- [x] Define GetUserAction (user_id: str) and GetUserObservation
- [x] Implement to_llm_content() returning @username (display_name)
- [x] Create `tools/get_user/impl.py` with GetUserExecutor
- [x] Create `tools/get_user/__init__.py` exporting GetUserTool

### Tool: FetchChannel (nice-to-have)

- [x] Create `tools/fetch_channel/definition.py`
- [x] Define FetchChannelAction (channel_id: str) and FetchChannelObservation
- [x] Implement to_llm_content()
- [x] Create `tools/fetch_channel/impl.py` with FetchChannelExecutor
- [x] Create `tools/fetch_channel/__init__.py` exporting FetchChannelTool

### Tool: finish

- [x] Create `tools/finish/definition.py`
- [x] Define FinishAction (tldr, narrative, action_items, participants)
- [x] Define FinishObservation
- [x] Create `tools/finish/impl.py` with FinishExecutor (trivial pass-through)
- [x] Create `tools/finish/__init__.py` exporting FinishTool

### Tools Package

- [x] Create `tools/__init__.py` exporting all tools
- [x] Implement `build_mattermost_tools(client)` factory function
- [x] Register tools with OpenHands registry

### Agent Factory

- [x] Create `agent.py` with `build_summarizer_agent()` function
- [x] Create agent with LLM + Mattermost tools
- [x] Return agent instance ready for Conversation

### Summarizer Facade

- [x] Create `summarizer.py` with MattermostSummarizer class
- [x] Implement from_config() and from_env() classmethods
- [x] Implement summarize(permalink_url) → SummaryResult
- [x] Parse permalink, build client, LLM, tools, agent
- [x] Create Conversation, send_message, run()
- [x] Scan events for FinishAction result
- [x] Return SummaryResult with metadata

### Error Classes

- [x] Create `exceptions.py` with PermalinkError, AuthenticationError, ThreadNotFoundError, AgentStuckError, ConfigError

### Package Init Exports

- [x] Update `__init__.py` to export MattermostSummarizer, SummaryResult, ConfigError classes
- [x] Export exceptions

### Testing Setup

- [x] Create `test_config.py` with config loading tests
- [x] Create `test_parse_permalink.py` with URL parsing tests
- [x] Create `test_client.py` with mock HTTP tests (mock httpx)
- [x] Create `test_models.py` with model serialization tests
- [x] Create `test_tools.py` with tool definition tests

### Documentation

- [x] Add docstrings to all public classes and methods
- [x] Create example usage in docstring of MattermostSummarizer
- [x] Add type hints throughout

## v1 Tasks Summary

Total: 45 tasks across 8 phases
Completed: 45/45
Remaining: 0