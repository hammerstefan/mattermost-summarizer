# Project Development Guidelines

This document defines baseline expectations for all development work in this project.

## Base Language

- **Python 3** is the base language for this project
- Use `python3` as the interpreter reference

## Package Management

- **uv** is the package manager for this project
- Use `uv` commands for dependency management:
  - `uv add <package>` - Add dependencies
  - `uv remove <package>` - Remove dependencies
  - `uv sync` - Sync dependencies with lock file
  - `uv lock` - Update lock file
  - `uv run <command>` - Run commands in project environment

## Code Quality Tools

### Linting

- **ruff** is the linter for this project
- Run with: `uv run ruff check .`
- Configuration should be in `pyproject.toml`

### Type Checking

- **mypy** and **pyright** are used for static type checking
- Run mypy with: `uv run mypy .`
- Run pyright with: `uv run pyright`

## Testing

- **pytest** is the testing framework
- Run tests with: `uv run pytest`
- Test files should follow `test_*.py` or `*_test.py` naming convention

## Development Workflow

1. Install dependencies: `uv sync`
2. Run linting: `uv run ruff check .`
3. Run type checking: `uv run mypy .` and/or `uv run pyright`
4. Run tests: `uv run pytest`


### Code Search

Use `semble search` to find code by describing what it does or naming a symbol/identifier, instead of grep:

```bash
semble search "authentication flow" ./my-project
semble search "save_pretrained" ./my-project
semble search "save model to disk" ./my-project --top-k 10
```

Use `semble find-related` to discover code similar to a known location (pass `file_path` and `line` from a prior search result):

```bash
semble find-related src/auth.py 42 ./my-project
```

`path` defaults to the current directory when omitted; git URLs are accepted.

If `semble` is not on `$PATH`, use `uvx --from "semble[mcp]" semble` in its place.

1. Start with `semble search` to find relevant chunks.
2. Inspect full files only when the returned chunk is not enough context.
3. Optionally use `semble find-related` with a promising result's `file_path` and `line` to discover related implementations.
4. Use grep only when you need exhaustive literal matches or quick confirmation of an exact string.
