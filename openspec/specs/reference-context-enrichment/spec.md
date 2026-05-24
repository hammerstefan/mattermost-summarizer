# Spec: Reference Context Enrichment

## Capability

Enrich each URL in the References block with a one-sentence context description extracted from the sub-agent's result text, helping the orchestrator judge relevance without fetching every URL.

## Requirements

### Requirement: Sentence context extracted per URL in References block
When `FetchReferenceExecutor` builds the References block after sub-agent completion, it SHALL extract one sentence of surrounding context for each URL from the sub-agent's result text.

The extraction SHALL:
- Locate each URL occurrence in the result text
- Return the sentence containing the URL, or the sentence immediately before/after if the URL is isolated
- Fall back to `"(no description available)"` if no sentence boundary is found within 300 characters of the URL
- Strip leading/trailing whitespace and punctuation artifacts

#### Scenario: URL in the middle of a sentence
- **WHEN** the result text contains "The proposed fix is in PR https://github.com/org/repo/pull/123 which addresses the root cause."
- **THEN** the extracted context is "The proposed fix is in PR https://github.com/org/repo/pull/123 which addresses the root cause."

#### Scenario: URL at the start of a sentence
- **WHEN** the result text contains "https://github.com/org/repo/issues/456 was filed to track the issue."
- **THEN** the extracted context is "https://github.com/org/repo/issues/456 was filed to track the issue."

#### Scenario: URL preceded by descriptive prose
- **WHEN** the result text contains "See the Launchpad bug for more details:\n\nhttps://bugs.launchpad.net/ubuntu/+bug/789"
- **THEN** the extracted context is "See the Launchpad bug for more details:" (the preceding sentence)

#### Scenario: URL with no nearby sentence boundary
- **WHEN** the result text contains a bare URL in a non-prose context (e.g. a bullet list with no surrounding sentences within 300 chars)
- **THEN** the extracted context is "(no description available)"

### Requirement: Sub-agent prompts instruct descriptive URL context
The `THREAD_FETCHER_PROMPT`, `GITHUB_RESEARCHER_PROMPT`, and `BUG_RESEARCHER_PROMPT` SHALL each include the instruction:

> When listing or mentioning any URLs or references in your summary, always include a one-sentence description of what the link is and why it matters — write it immediately before or after the URL.

The `FILE_FETCHER_PROMPT` SHALL NOT include this instruction.

#### Scenario: Thread fetcher prompt includes link description instruction
- **WHEN** a `thread_fetcher` sub-agent is spawned
- **THEN** its system message includes the instruction to write one-sentence descriptions near every URL

#### Scenario: File fetcher prompt does not include link description instruction
- **WHEN** a `file_fetcher` sub-agent is spawned
- **THEN** its system message does NOT include the link description instruction

### Requirement: Enriched References block format
The References block injected into the result SHALL use the format:

```
---
References found in result:
Found the following references in the content:

1. <url> (<type>) — <context sentence>
2. <url> (<type>) — <context sentence>

Current depth: <N>/<max>
You may delegate to appropriate sub-agents to fetch additional context.
```

Where `<context sentence>` is the extracted sentence context for each URL (without the URL itself to avoid duplication).

#### Scenario: References block with context per URL
- **WHEN** the sub-agent result text contains "The fix is in PR https://github.com/org/repo/pull/1 which resolves the issue" and "Bug https://bugs.launchpad.net/ubuntu/+bug/2 was also noted"
- **THEN** the References block lists:
  1. `https://github.com/org/repo/pull/1 (GitHub issue/PR) — The fix is in PR which resolves the issue`
  2. `https://bugs.launchpad.net/ubuntu/+bug/2 (Launchpad bug) — Bug was also noted`

#### Scenario: References block when depth limit is reached
- **WHEN** the current depth has reached `max_depth`
- **THEN** the block says "Maximum reference depth reached. Do not follow further references." instead of "You may delegate to appropriate sub-agents to fetch additional context."

#### Scenario: No followable URLs in result
- **WHEN** the sub-agent result contains no URLs matching known patterns
- **THEN** no "References found in result" section is appended
- **THEN** the result is returned as-is