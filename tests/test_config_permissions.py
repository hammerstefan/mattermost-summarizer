"""Tests for config file permissions checking."""

from pathlib import Path
from unittest.mock import patch

from mattermost_summarizer.utils import check_config_file_permissions


class TestCheckConfigFilePermissions:
    def _capture_stderr(self, fn: object) -> str:
        import io
        import sys

        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            fn()  # type: ignore[operator]
            return sys.stderr.getvalue()
        finally:
            sys.stderr = old_stderr

    def test_warning_emitted_for_0644_mode(self, tmp_path: Path) -> None:
        config_file = tmp_path / "test.toml"
        config_file.write_text('[mattermost]\ntoken = "s"\n[llm]\napi_key = "k"')
        config_file.chmod(0o644)
        stderr = self._capture_stderr(lambda: check_config_file_permissions(config_file))
        assert "Warning: Config file" in stderr
        assert "chmod 0600" in stderr

    def test_warning_emitted_for_0755_mode(self, tmp_path: Path) -> None:
        config_file = tmp_path / "test.toml"
        config_file.write_text('[mattermost]\ntoken = "s"\n[llm]\napi_key = "k"')
        config_file.chmod(0o755)
        stderr = self._capture_stderr(lambda: check_config_file_permissions(config_file))
        assert "Warning: Config file" in stderr

    def test_no_warning_for_0600_mode(self, tmp_path: Path) -> None:
        config_file = tmp_path / "test.toml"
        config_file.write_text('[mattermost]\ntoken = "s"\n[llm]\napi_key = "k"')
        config_file.chmod(0o600)
        stderr = self._capture_stderr(lambda: check_config_file_permissions(config_file))
        assert "chmod 0600" not in stderr

    def test_warning_emitted_for_0640_mode(self, tmp_path: Path) -> None:
        config_file = tmp_path / "test.toml"
        config_file.write_text('[mattermost]\ntoken = "s"\n[llm]\napi_key = "k"')
        config_file.chmod(0o640)
        stderr = self._capture_stderr(lambda: check_config_file_permissions(config_file))
        assert "chmod 0600" in stderr

    def test_no_warning_for_0400_mode(self, tmp_path: Path) -> None:
        config_file = tmp_path / "test.toml"
        config_file.write_text('[mattermost]\ntoken = "s"\n[llm]\napi_key = "k"')
        config_file.chmod(0o400)
        stderr = self._capture_stderr(lambda: check_config_file_permissions(config_file))
        assert "chmod 0600" not in stderr

    def test_symlink_target_permissions_checked(self, tmp_path: Path) -> None:
        target = tmp_path / "target.toml"
        target.write_text('[mattermost]\ntoken = "s"\n[llm]\napi_key = "k"')
        target.chmod(0o644)
        link = tmp_path / "link.toml"
        link.symlink_to(target)
        stderr = self._capture_stderr(lambda: check_config_file_permissions(link))
        assert "chmod 0600" in stderr

    def test_nonexistent_file_no_warning(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "nonexistent.toml"
        stderr = self._capture_stderr(lambda: check_config_file_permissions(nonexistent))
        assert "chmod 0600" not in stderr

    def test_oserror_from_stat_handled(self, tmp_path: Path) -> None:
        config_file = tmp_path / "test.toml"
        config_file.write_text('[mattermost]\ntoken = "s"\n[llm]\napi_key = "k"')
        with patch("os.stat", side_effect=OSError("Permission denied")):
            stderr = self._capture_stderr(lambda: check_config_file_permissions(config_file))
        assert "chmod 0600" not in stderr
