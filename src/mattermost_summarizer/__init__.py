"""Mattermost Conversation Summarizer.

An agentic tool that summarizes Mattermost threads using the OpenHands SDK.
"""

from mattermost_summarizer.config import MattermostSummarizerConfig
from mattermost_summarizer.exceptions import (
    AgentStuckError,
    AuthenticationError,
    ConfigError,
    PermalinkError,
    ThreadNotFoundError,
)
from mattermost_summarizer.models import SummaryMeta, SummaryResult
from mattermost_summarizer.summarizer import MattermostSummarizer

__all__ = [
    "MattermostSummarizer",
    "SummaryResult",
    "SummaryMeta",
    "MattermostSummarizerConfig",
    "PermalinkError",
    "AuthenticationError",
    "ThreadNotFoundError",
    "AgentStuckError",
    "ConfigError",
]
