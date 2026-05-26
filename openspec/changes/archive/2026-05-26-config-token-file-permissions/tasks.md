## 1. Code Changes — `summarize.py`

- [x] 1.1 Add `check_config_file_permissions(path: Path) -> None` helper function that:
  - Resolves symlinks via `path.resolve()`
  - Calls `os.stat()` on the resolved path (catches `OSError` gracefully)
  - Checks `stat_result.st_mode & 0o077`
  - Prints warning to stderr if world-readable, with actual octal mode and recommended chmod
- [x] 1.2 Call `check_config_file_permissions(config_path)` after the config file existence check and before `MattermostSummarizerConfig.from_config()`

## 2. Documentation — `config.py`

- [x] 2.1 Add a note to the `MattermostSummarizerConfig` class docstring under "Configuration" stating: "Config files containing tokens MUST have filesystem permissions of `0600` to prevent other local users from reading sensitive values."

## 3. Documentation — `README.md`

- [x] 3.1 In the "Configuration" section, add a note after the TOML example: "**Security note**: store tokens in environment variables rather than in TOML files when deploying on multi-user systems — TOML files contain plaintext secrets that require filesystem-level `0600` permissions."
- [x] 3.2 In the "Environment Variables" section, add a sentence: "Environment variables are the recommended approach for production deployments to avoid plaintext secrets on disk."

## 4. Tests

- [x] 4.1 Add unit test `tests/test_config_permissions.py` with:
  - Test that warning is emitted for `0644` mode
  - Test that warning is emitted for `0755` mode
  - Test that no warning for `0600` mode
  - Test that warning is emitted for `0640` mode
  - Test that no warning for `0400` mode (owner-only)
  - Test symlink target permissions are checked
  - Test graceful handling when file doesn't exist
