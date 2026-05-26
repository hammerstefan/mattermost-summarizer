## Context

Tool executors in mattermost-summarizer catch exceptions broadly and expose raw exception strings to the LLM via the `error` field in observations. This creates a security risk where internal implementation details (file paths, network info, API structures) could influence LLM behavior.

Additionally, logging currently goes exclusively to a file with no stderr output during normal operation, making real-time debugging difficult without verbose mode.

**Current state of error handling:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Tool catches Exception → error=str(e) → Observation.error         │
│                                           → to_llm_content()         │
│                                           → LLM receives raw details │
└─────────────────────────────────────────────────────────────────────┘
```

**Logging state:**
- Normal operation: All logs → file only (no stderr)
- Verbose mode: Same (no change in current implementation)

## Goals / Non-Goals

**Goals:**
- Sanitize all tool error messages sent to LLM (no raw `str(e)`)
- Implement logging verbosity ladder for operators
- Enable stderr output in verbose/debug mode while keeping normal output clean
- Maintain full traceback information in log files for debugging

**Non-Goals:**
- Change tool observable behavior (error field still tells LLM something failed)
- Modify the OpenHands SDK or its error event handling
- Add new capabilities (defensive change only)
- Change exception handling in application logic (only surface-level sanitization)

## Decisions

### Decision 1: Error Message Sanitization Pattern

**Chosen approach:** Replace `str(e)` with generic user-safe messages in all tool executors.

```python
# Before
except Exception as e:
    return FetchGitHubIssueObservation(error=str(e))

# After
except Exception as e:
    logger.error("Unexpected error in GitHub fetch: %s", e, exc_info=True)
    return FetchGitHubIssueObservation(error="An internal error occurred.")
```

**Rationale:** Simple, consistent, no chance of leaking internal details. The trade-off is operators need to check logs for debugging, which is acceptable since logs are always written.

**Alternatives considered:**
- Structured error codes: Too complex for the benefit
- Exception type mapping to messages: Still risks leaking type names

### Decision 2: Logging Verbosity Ladder

**Chosen approach:** Map error types to log levels based on expected frequency and operator action required.

| Scenario | Log Level | Rationale |
|----------|-----------|-----------|
| Rate limited (429/403) | `log.info` | Expected when token not configured; no action needed |
| Invalid URL format | `log.debug` | Common, not actionable |
| Network timeout | `log.warning` | May indicate connectivity issues |
| Unexpected exception | `log.error` with `exc_info=True` | Requires operator attention |

**Rationale:** Keeps normal operation quiet while providing actionable info in verbose mode.

### Decision 3: Stderr Output Control

**Chosen approach:** Dual output (file + stderr) controlled by verbosity level.

```
Normal mode:     logger.debug/info/warning/error → file only
Verbose mode (-v): logger.info → stderr
                  logger.warning/error → stderr + file
```

**Rationale:** Operators can enable real-time debugging without code changes.

**Implementation:** Use Python's logging module with a `logging.StreamHandler` attached only when verbose mode is active.

### Decision 4: Critic Error Feedback

**Chosen approach:** Log JSON parsing errors but use generic feedback string.

```python
# In critic.py
except (json.JSONDecodeError, ValueError, AttributeError) as e:
    logger.debug("Critic JSON parsing failed: %s", e)
    return CriticEvaluation(
        score=0.5,
        feedback="Critic evaluation failed due to parsing error. Assuming fair quality.",
    )
```

**Rationale:** Low risk since exception comes from Python/json, not user content. But logging at debug level helps with debugging if needed.

## Risks / Trade-offs

[Risk] Operators may not know to check logs for debugging details
→ **Mitigation:** Document the logging behavior; generic error messages include hint about verbose mode

[Risk] Changing error message format may break existing error handling downstream
→ **Mitigation:** Only changing message content, not field structure; fully backward compatible

[Risk] Verbose mode stderr output may be too noisy
→ **Mitigation:** Only errors/warnings go to stderr; debug/info still file-only in normal mode

## Open Questions

1. Should we add a `--verbose` / `-v` flag to `summarize.py` CLI, or rely on environment variable?
2. Do we want to add a `--debug` flag for even more verbose output (all log levels to stderr)?
3. Should the `fetch_reference_tool.py` error message be further sanitized since it contains sub-agent LLM content?
