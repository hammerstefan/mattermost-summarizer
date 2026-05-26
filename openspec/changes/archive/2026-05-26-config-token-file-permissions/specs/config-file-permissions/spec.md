# Config File Permissions — Defensive Check

## ADDED Requirements

### Requirement: Config file permissions check on startup

`summarize.py` SHALL check the file mode of the config file path passed via `--config` (or the default `mattermost-summarizer.toml`) before loading. If the file is world-readable (mode bits that grant read access to others, i.e., `mode & 0o077`), a warning SHALL be written to stderr recommending the file be changed to `0600`.

#### Scenario: Config file is world-readable

- **WHEN** the user runs `summarize.py --config /path/to/config.toml` where the file mode grants read access to group or others (`mode & 0o077 != 0`)
- **THEN** the program SHALL print a warning to stderr: `"Warning: Config file '/path/to/config.toml' has permissions {octal_mode} — consider 'chmod 0600 {filename}' to restrict access."` and continue execution

#### Scenario: Config file is properly restricted

- **WHEN** the user runs `summarize.py --config /path/to/config.toml` where the file mode does not grant group/others read access (`mode & 0o077 == 0`)
- **THEN** no warning SHALL be emitted for permissions

#### Scenario: Config file does not exist

- **WHEN** the config file path does not exist
- **THEN** the existing error `"Error: Config file not found: ..."` SHALL be emitted before the permissions check runs

#### Scenario: Config file path is a symlink

- **WHEN** the config file path resolves to a symlink
- **THEN** the file mode of the target file SHALL be checked (not the symlink itself)

### Requirement: Config file permissions documentation

The `MattermostSummarizerConfig` class docstring in `config.py` SHALL include a note that TOML config files containing tokens MUST have `0600` permissions when stored on disk.

### Requirement: Production deployment guidance in README

The README SHALL include a note in the "Environment Variables" section stating that environment variables are the preferred mechanism for production deployments since config files store tokens in plaintext.
