# Testing Guide

## Running Pytest in This Environment

### The Problem
`uv run pytest` may use a different Python environment than expected, causing
`ModuleNotFoundError` for packages that appear installed. The `openhands.tools`
module was not found when running via `uv run pytest`, but worked fine with
direct `uv run python`.

### The Solution

**1. Use the local venv Python directly:**
```bash
.venv/bin/python -m pytest tests/
```

**2. Install test dependencies first (if needed):**
```bash
uv pip install pytest pytest-asyncio pytest-httpserver respx
```

**3. If still having import issues, install the package in dev mode:**
```bash
uv pip install -e .
```

### Key Findings
- `uv run pytest` → uses different Python than `uv run python`
- `.venv/bin/python -m pytest` → uses the correct local venv
- `uv pip install` → installs to the local venv
- Test dependencies from `pyproject.toml` `[project.optional-dependencies] dev`
  need explicit install

### Quick Test Command
```bash
cd /path/to/multi-agent && uv pip install pytest pytest-asyncio pytest-httpserver respx && .venv/bin/python -m pytest tests/ -v
```

### Running Specific Test Files
```bash
.venv/bin/python -m pytest tests/test_multi_agent.py -v
.venv/bin/python -m pytest tests/test_levels.py -v
.venv/bin/python -m pytest tests/test_tools.py -v
```

### Code Quality Checks
```bash
# Lint
uv run ruff check src/

# Type check (mypy)
uv run mypy src/

# Type check (pyright)
uv run pyright src/
```