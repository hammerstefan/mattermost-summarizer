## Why

Mattermost thread content is ingested directly into the LLM context without sanitization. A malicious user could craft messages attempting to override system instructions or manipulate the `finish` tool output via prompt injection.

## What Changes

- **Preamble injection**: Add a clear "external content" delimiter in the initial user message to help the LLM distinguish user content from system instructions
- **Input sanitization**: Strip known prompt injection patterns (e.g., "ignore previous instructions", "disregard system prompt") from thread content before LLM ingestion
- **Output validation**: Add suspicious pattern detection in finish action validators as a defense-in-depth measure
- **Documentation**: Document the threat model for thread injection in the security audit

## Capabilities

### New Capabilities

- `thread-content-sanitization`: Input sanitization layer for Mattermost thread content before LLM ingestion, including injection pattern detection and removal

### Modified Capabilities

<!-- No existing spec behavior changes - this is a security hardening that preserves existing behavior -->

## Impact

- **Modified**: `src/mattermost_summarizer/summarizer.py` — prefetch path (add preamble)
- **Modified**: `src/mattermost_summarizer/tools/fetch_thread/impl.py` — `to_llm_content()` method
- **Modified**: `src/mattermost_summarizer/levels/base.py` and level files — output validators
- **New**: `src/mattermost_summarizer/sanitization.py` (or inline) — sanitization utilities
