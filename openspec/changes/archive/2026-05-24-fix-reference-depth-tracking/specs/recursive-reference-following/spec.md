## MODIFIED Requirements

### Requirement: Recursive reference following
The system SHALL follow referenced URLs recursively up to a configurable depth. Depth represents the nesting level in the reference chain — siblings found in the same result share the same depth.

The `FetchReferenceExecutor`, upon completing a sub-agent delegation at depth N, SHALL pre-register each followable URL found in the result at depth N+1 on the `ReferenceTracker`. When the executor processes a new `fetch_reference` call, it SHALL look up the URL's registered depth from the tracker and check it against `max_depth`. The root URL (not found in any result) is assigned depth 0.

The `ReferenceTracker`:
- SHALL store `followed_urls: dict[str, int]` mapping each fetched URL to the depth it was fetched at
- SHALL store `pending_urls: dict[str, int]` mapping URLs surfaced in the most recent References block to their child depth
- SHALL provide `register_pending(url: str, depth: int)` for the executor to register URLs at injection time
- SHALL provide `get_depth_for(url: str) -> int | None` returning the registered depth (from pending or followed), or `None` for unregistered URLs (interpreted as depth 0 by the executor)
- SHALL provide `mark_followed(url: str, depth: int)` recording a URL as followed at the given depth
- SHALL NOT have a `current_depth: int` field or `increment_depth()` method

#### Scenario: No URLs followed (depth budget intact)
- **WHEN** the root thread result contains no followable URLs
- **THEN** no References block is appended
- **THEN** the orchestrator receives only the sub-agent result text
- **THEN** only the root thread is fetched

#### Scenario: One URL followed
- **WHEN** the root thread result references a Launchpad bug
- **THEN** the References block lists the LP bug URL at depth 1
- **THEN** the orchestrator calls `fetch_reference` for the bug URL
- **THEN** the executor registers the LP bug at depth 1 in `followed_urls`
- **THEN** after bug_researcher completes, no further URLs are surfaced (or all are at depth 2, which requires another `fetch_reference` call)
- **THEN** the orchestrator synthesizes and calls finish

#### Scenario: Three levels of nesting (chain)
- **WHEN** thread A's result surfaces thread B's URL (depth 1)
- **AND** thread B's result surfaces thread C's URL (depth 2)
- **AND** thread C's result surfaces thread D's URL (depth 3)
- **AND** `max_depth=3`
- **THEN** `fetch_reference(thread_D)` succeeds (depth 3)
- **THEN** `fetch_reference` for depth 4 URLs (surfaced from thread D) returns a depth-exceeded error
- **THEN** the orchestrator synthesizes and calls finish

#### Scenario: Multiple siblings at the same depth do not compete
- **WHEN** the root thread result surfaces 6 followable GitHub URLs at depth 1
- **THEN** all 6 calls to `fetch_reference` succeed because siblings share depth 1
- **THEN** each URL is registered at depth 1 in `followed_urls`
- **THEN** `max_depth` is not exceeded by sibling count alone

#### Scenario: Already-followed URL is not re-fetched
- **WHEN** the orchestrator calls `fetch_reference(url)` for a URL already present in `followed_urls`
- **THEN** the executor returns an error observation with "URL has already been followed"
- **THEN** no sub-agent is spawned

### Requirement: URL classification for delegation routing
Python SHALL classify URLs found in sub-agent result text and list them in a "References found in result" block appended to the result. Each URL entry SHALL include:

- The URL and its classified type (e.g. "GitHub issue/PR", "Launchpad bug")
- One sentence of surrounding context extracted from the result text (without the URL itself)

The injected block SHALL use the format:

```
---
References found in result:
Found the following references in the content:

1. <url> (<type>) — <context sentence>
2. <url> (<type>) — <context sentence>

Current depth: <N>/<max>
You may delegate to appropriate sub-agents to fetch additional context.
```

If no followable URLs are found, no block is appended and the result is returned as-is.

Classification rules (unchanged):

| URL Pattern | Type |
|---|---|
| `chat.{server}/{team}/pl/{post_id}` | Mattermost thread |
| `bugs.launchpad.net/.../+bug/{id}` | Launchpad bug |
| `github.com/{owner}/{repo}/issues/{id}` | GitHub issue/PR |
| `github.com/{owner}/{repo}/pull/{id}` | GitHub issue/PR |
| Mattermost file IDs | Mattermost file |

#### Scenario: Classification routes to correct sub-agent
- **WHEN** the result text contains a URL `https://bugs.launchpad.net/ubuntu/+bug/12345`
- **THEN** it is classified as `launchpad_bug` and listed in the References block with type "Launchpad bug"
- **THEN** the orchestrator calls `fetch_reference` for the URL

#### Scenario: Multiple URL types in same thread
- **WHEN** thread content contains a GitHub PR URL, a Launchpad bug URL, and a Mattermost permalink
- **THEN** all three are classified and listed in a single References block with context sentences
- **THEN** the orchestrator decides which are relevant and calls `fetch_reference` for each chosen URL

#### Scenario: No followable URLs found
- **WHEN** the delegation result contains no URLs matching any known pattern
- **THEN** no References block is appended
- **THEN** the raw result text is returned to the orchestrator

## REMOVED Requirements

### Requirement: Depth counted as total fetch count
**Reason**: The global `current_depth` counter treats sibling fetches as consuming depth slots. With `max_depth=3`, the 4th sibling from the root is blocked even when no nesting has occurred. This misrepresents the intended nesting-depth semantics.
**Migration**: Depth is now stored per-URL in `followed_urls: dict[str, int]` and `pending_urls: dict[str, int]`. The `current_depth`, `increment_depth()`, `can_follow_deeper()` API is replaced by `register_pending()` and `get_depth_for()`. Siblings share the same depth because all are registered at the same parent-depth+1 value at injection time.
