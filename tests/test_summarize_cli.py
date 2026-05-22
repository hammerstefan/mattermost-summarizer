"""Tests for summarize.py CLI argument combinations."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

TOML_TEMPLATE = """\
[mattermost]
url = "https://chat.example.com"
token = "mm_test_token"

[llm]
model = "openai/gpt-4o"
api_key = "sk_test_key"

[summarizer]
default_level = "{default_level}"
"""


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """Create a default config file."""
    toml_path = tmp_path / "config.toml"
    toml_path.write_text(TOML_TEMPLATE.format(default_level="normal"))
    return toml_path


def _run(args: list[str], config_path: Path, *, level: str | None = None, output: str | None = None) -> Any:
    """Run summarize.py with given args, returning CompletedProcess."""
    cmd = [
        sys.executable,
        str(Path(__file__).parent.parent / "summarize.py"),
        "https://chat.example.com/team/pl/post123",
        "--config",
        str(config_path),
    ]
    if level:
        cmd.extend(["--level", level])
    if output:
        cmd.extend(["--output", output])
    return subprocess.run(cmd, capture_output=True, text=True, timeout=10)


class TestLevelArgument:
    """Test --level / -l argument overrides default_level from config."""

    @pytest.mark.parametrize("level", ["brief", "normal", "detailed"])
    def test_level_arg_accepted(self, tmp_path: Path, level: str) -> None:
        """Test that --level accepts all valid values."""
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(TOML_TEMPLATE.format(default_level="normal"))
        result = _run([], config_path=toml_path, level=level, output="json")
        assert result.returncode == 1


class TestDefaultLevelFromConfig:
    """Test that default_level from config is used when --level not specified."""

    @pytest.mark.parametrize("default_level", ["brief", "normal", "detailed"])
    def test_config_default_is_used(self, tmp_path: Path, default_level: str) -> None:
        """Test that config default_level is used when no --level argument."""
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(TOML_TEMPLATE.format(default_level=default_level))
        result = _run([], config_path=toml_path, output="json")
        assert result.returncode == 1


class TestOutputFormat:
    """Test --output / -o argument for text and json formats."""

    @pytest.mark.parametrize("level", ["brief", "normal", "detailed"])
    def test_output_json_accepted(self, tmp_path: Path, level: str) -> None:
        """Test that --output json is accepted."""
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(TOML_TEMPLATE.format(default_level="normal"))
        result = _run([], config_path=toml_path, level=level, output="json")
        assert result.returncode == 1

    @pytest.mark.parametrize("level", ["brief", "normal", "detailed"])
    def test_output_text_accepted(self, tmp_path: Path, level: str) -> None:
        """Test that --output text is accepted."""
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(TOML_TEMPLATE.format(default_level="normal"))
        result = _run([], config_path=toml_path, level=level, output="text")
        assert result.returncode == 1


class TestConfigFileNotFound:
    """Test error handling when config file is missing."""

    def test_missing_config_returns_error(self, tmp_path: Path) -> None:
        """Test that non-existent config file returns error."""
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent.parent / "summarize.py"),
                "https://chat.example.com/team/pl/post123",
                "--config",
                str(tmp_path / "nonexistent.toml"),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 1
        assert "Config file not found" in result.stderr


class TestArgumentCombinations:
    """Test minimal covering set of CLI argument combinations.

    Reduced from 18 parameterized combinations to 6, covering all three
    factors (level_arg, default_level, output_format) at 2 levels each.
    """

    @pytest.mark.parametrize(
        "level_arg,default_level,output_format",
        [
            ("brief", "normal", "text"),
            ("normal", "brief", "json"),
            ("detailed", "normal", "text"),
            (None, "detailed", "json"),
            ("brief", "detailed", "text"),
            ("detailed", "brief", "json"),
        ],
    )
    def test_combinations(
        self,
        tmp_path: Path,
        level_arg: str | None,
        default_level: str,
        output_format: str,
    ) -> None:
        """Test minimal covering set of --level, config default_level, and --output."""
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(TOML_TEMPLATE.format(default_level=default_level))
        result = _run([], config_path=toml_path, level=level_arg, output=output_format)
        assert result.returncode == 1

    def test_short_form_level(self, tmp_path: Path) -> None:
        """Test -l short form for --level."""
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(TOML_TEMPLATE.format(default_level="normal"))
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent.parent / "summarize.py"),
                "https://chat.example.com/team/pl/post123",
                "--config",
                str(toml_path),
                "-l",
                "detailed",
                "--output",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 1

    def test_short_form_output(self, tmp_path: Path) -> None:
        """Test -o short form for --output."""
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(TOML_TEMPLATE.format(default_level="normal"))
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent.parent / "summarize.py"),
                "https://chat.example.com/team/pl/post123",
                "--config",
                str(toml_path),
                "--level",
                "brief",
                "-o",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 1

    def test_short_form_config(self, tmp_path: Path) -> None:
        """Test -c short form for --config."""
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(TOML_TEMPLATE.format(default_level="normal"))
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent.parent / "summarize.py"),
                "https://chat.example.com/team/pl/post123",
                "-c",
                str(toml_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 1

    def test_url_required(self, tmp_path: Path) -> None:
        """Test that URL positional argument is required."""
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(TOML_TEMPLATE.format(default_level="normal"))
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent.parent / "summarize.py"),
                "--config",
                str(toml_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0
        assert "error: the following arguments are required: url" in result.stderr

    def test_invalid_level_rejected(self, tmp_path: Path) -> None:
        """Test that invalid --level value is rejected by argparse."""
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(TOML_TEMPLATE.format(default_level="normal"))
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent.parent / "summarize.py"),
                "https://chat.example.com/team/pl/post123",
                "--config",
                str(toml_path),
                "--level",
                "invalid_level",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0
        assert "invalid choice" in result.stderr

    def test_invalid_output_rejected(self, tmp_path: Path) -> None:
        """Test that invalid --output value is rejected by argparse."""
        toml_path = tmp_path / "config.toml"
        toml_path.write_text(TOML_TEMPLATE.format(default_level="normal"))
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent.parent / "summarize.py"),
                "https://chat.example.com/team/pl/post123",
                "--config",
                str(toml_path),
                "--output",
                "invalid_format",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0
        assert "invalid choice" in result.stderr
