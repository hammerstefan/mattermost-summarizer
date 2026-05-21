"""Tests for config loading."""

import pytest
from pydantic import HttpUrl, SecretStr, ValidationError

from mattermost_summarizer.config import MattermostSummarizerConfig


class TestMattermostSummarizerConfig:
    def test_from_env_missing_required(self) -> None:
        with pytest.raises(ValidationError):
            MattermostSummarizerConfig.from_env()

    def test_from_config_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            MattermostSummarizerConfig.from_config("/nonexistent/config.toml")


class TestConfigEnvVarLoading:
    def test_config_defaults(self) -> None:
        config = MattermostSummarizerConfig(
            mattermost_url=HttpUrl("https://chat.example.com"),
            mattermost_token=SecretStr("test-token"),
            llm_api_key=SecretStr("test-key"),
        )
        assert str(config.mattermost_url) == "https://chat.example.com/"
        assert config.llm_model == "openai/gpt-4o"
        assert config.llm_base_url is None

    def test_config_custom_values(self) -> None:
        config = MattermostSummarizerConfig(
            mattermost_url=HttpUrl("https://mattermost.example.com"),
            mattermost_token=SecretStr("my-secret-token"),
            llm_api_key=SecretStr("llm-secret-key"),
            llm_model="anthropic/claude-3-sonnet",
            llm_base_url="https://api.anthropic.com",
        )
        assert str(config.mattermost_url) == "https://mattermost.example.com/"
        assert config.llm_model == "anthropic/claude-3-sonnet"
        assert config.llm_base_url == "https://api.anthropic.com"

    def test_secret_str_not_exposed_in_repr(self) -> None:
        config = MattermostSummarizerConfig(
            mattermost_url=HttpUrl("https://chat.example.com"),
            mattermost_token=SecretStr("secret-token"),
            llm_api_key=SecretStr("llm-key"),
        )
        repr_str = repr(config)
        assert "secret-token" not in repr_str
        assert "llm-key" not in repr_str
