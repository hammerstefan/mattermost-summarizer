## Why

API tokens (`mattermost_token`, `llm_api_key`, `github_token`) are stored in TOML config files. While Pydantic v2's `SecretStr` masks values in logs, the tokens exist in plaintext on disk. If config files are world-readable (e.g., `0644`), any local user can read these sensitive credentials. This is especially risky in multi-user systems or shared hosting environments.

## What Changes

- Add a startup permission check in `summarize.py` that detects if the config file is world-readable (`mode & 0o077`)
- Emit a warning message to stderr when world-readable config is detected, recommending `0600` permissions
- Document in `config.py`'s docstring that config files must have `0600` permissions
- Update `README.md` to emphasize that environment variables are preferred for production deployments

## Capabilities

### New Capabilities

- `config-file-permissions`: Permissions checking for TOML config files that contain sensitive tokens. Checks after the file is loaded and warns if the file mode would allow access from other users on the system.

### Modified Capabilities

- None — this is a new defensive feature that doesn't change existing spec behavior.

## Impact

- **Code**: `summarize.py` gains a `check_config_file_permissions()` helper called before `MattermostSummarizerConfig.from_config()`.
- **Config**: No changes to config schema — purely additive warning.
- **Docs**: README section on configuration and `config.py` docstring updated.
