## MODIFIED Requirements

### Requirement: Recursive reference following
The system SHALL follow referenced URLs recursively up to a configurable depth.

The orchestrator:
- SHALL receive classified URLs automatically as an injected user message after each delegation round — Python performs classification between `run()` segments; no LLM tool call is needed
- SHALL use `follow_url(url)` to register a URL as followed before delegating to the corresponding sub-agent
- SHALL stop delegating when `follow_url` returns `depth_exceeded`
- SHALL skip URLs where `follow_url` returns `already_followed`

#### Scenario: Recursion depth 1 (no recursion)
- **WHEN** the root thread contains no referenced URLs
- **THEN** no classified URL message is injected after the initial delegation
- **THEN** only thread_fetcher is delegated
- **THEN** no further delegation rounds occur
- **THEN** max_reference_depth is not exceeded

#### Scenario: Recursion depth 2
- **WHEN** the root thread references a Launchpad bug
- **THEN** after thread_fetcher completes, Python classifies the result and injects a URL list message
- **THEN** the orchestrator calls `follow_url` for the bug URL and receives `success`
- **THEN** the orchestrator delegates to bug_researcher
- **THEN** after bug_researcher completes, Python injects no further URLs (none found or depth exceeded)
- **THEN** orchestrator synthesizes and calls finish

#### Scenario: Recursion depth 3
- **WHEN** thread A references thread B, and thread B references thread C
- **THEN** depth 1: thread_fetcher fetches thread A; Python injects thread B's URL
- **THEN** orchestrator calls `follow_url(thread_B_url)` → success; delegates thread_fetcher for thread B
- **THEN** depth 2: thread_fetcher fetches thread B; Python injects thread C's URL
- **THEN** orchestrator calls `follow_url(thread_C_url)` → success; delegates thread_fetcher for thread C
- **THEN** depth 3: thread_fetcher fetches thread C; Python injects no further URLs (depth limit reached or no new URLs)
- **THEN** orchestrator synthesizes and calls finish

## MODIFIED Requirements

### Requirement: URL classification for delegation routing
Python SHALL classify found URLs after each delegation round and inject the classified list as a user message before the orchestrator's next LLM step.

Classification rules are identical to prior spec:

| URL Pattern | Sub-agent |
|-------------|----------|
| `chat.{server}/{team}/pl/{post_id}` | thread_fetcher |
| `bugs.launchpad.net/.../+bug/{id}` | bug_researcher |
| `github.com/{owner}/{repo}/issues/{id}` | github_researcher |
| `github.com/{owner}/{repo}/pull/{id}` | github_researcher |
| Mattermost file IDs | file_fetcher |

The injected message SHALL use the format:
```
References found in delegation result:
1. <url>  (<type> → <sub-agent>)
2. <url>  (<type> → <sub-agent>)
Depth: N/M — can follow more

Decide which (if any) are relevant and call follow_url before delegating.
```

If no followable URLs are found, no message is injected and `run()` continues without pausing.

#### Scenario: Classification routes to correct sub-agent
- **WHEN** Python extracts a URL `https://bugs.launchpad.net/ubuntu/+bug/12345` from delegation result
- **THEN** it classifies as `launchpad_bug → bug_researcher`
- **THEN** the injected message lists the URL with its type and target sub-agent

#### Scenario: Multiple URL types in same thread
- **WHEN** thread content contains a GitHub PR URL, a Launchpad bug URL, and a Mattermost permalink
- **THEN** Python classifies all three and injects a single message listing all three with types
- **THEN** the orchestrator decides which are relevant and calls `follow_url` for each chosen URL

#### Scenario: No followable URLs found
- **WHEN** the delegation result contains no URLs matching any known pattern
- **THEN** Python does NOT inject any message
- **THEN** `run()` continues without pausing for URL injection
