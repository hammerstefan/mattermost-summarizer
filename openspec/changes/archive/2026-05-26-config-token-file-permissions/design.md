## Context

`summarize.py` loads credentials from a TOML config file via `MattermostSummarizerConfig.from_config()`. The file contains sensitive tokens (`mattermost_token`, `llm_api_key`, `github_token`) in plaintext. On a multi-user Unix system, a config file created with default permissions (`0644`) can be read by any local user via `cat` or similar tools.

The issue is informational in the current workflow — no enforcement exists. This design adds a lightweight warning mechanism at startup with documentation.

## Goals / Non-Goals

**Goals:**
- Warn users when their config file is world-readable, without blocking execution
- Guide users toward the correct fix (`chmod 0600`)
- Update documentation to emphasize environment variables for production
- Add a permissions check for the specific config file path passed via `--config`

**Non-Goals:**
- Changing file permissions programmatically (requires elevated privileges, risky)
- Scanning working directory for other TOML files
- Enforcing permissions at the Pydantic level (config is already loaded by then)
- Modifying the config schema

## Decisions

### 1. Check `os.stat(filepath).st_mode` after TOML load succeeds

Checking before `from_config()` would miss the case where the file doesn't exist (the existing error check handles that separately). Checking before load also handles "file doesn't exist" gracefully. Checking after load is fine too.

We use `os.stat()` on the resolved path (to follow symlinks) and check `mode & 0o077`.

**Alternative considered**: Using `pathlib.Path.stat()` — equivalent. Using Python's `os` module keeps the intent clear.
**Alternative considered**: Checking `os.access(path, os.W_OK)` — this tests effective permissions (what the current user *can* do), not what other users *could* do. We want the actual mode bits.

### 2. Warning goes to stderr, does not block execution

Security warnings that halt execution cause frustration and may prevent legitimate use. The warning guides users toward remediation without blocking the tool. This follows common practice (e.g., `pip`, `npm` warn on issues but don't block).

### 3. No coverage for `from_env()` path

Loading config purely from environment variables (`MattermostSummarizerConfig.from_env()`) has no file to check. The check is scoped to `summarize.py`'s `--config` path. Library users who call `from_config()` directly can opt in if they choose.

## Risks / Trade-offs

- **Risk**: Warning is easy to miss in CI.

  **Mitigation**: Document the recommendation explicitly so it appears in runbooks and setup scripts.
- **Risk**: Platform differences — on Windows, file modes work differently.

  **Mitigation**: The check uses `stat` which is available on all Unix-like platforms. On non-Unix, the check gracefully no-ops (a future improvement could use `ctypes` on Windows). For now, the code handles `OSError` from `stat()`.
- **Trade-off**: Warning on every run could be noisy.

  **Mitigation**: The warning targets world-readable specifically (`mode & 0o077`); `0640` (group-readable) also triggers. Most single-user systems won't trigger this.
