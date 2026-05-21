"""Tools package for mattermost-summarizer."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from openhands.sdk.tool.spec import Tool

from mattermost_summarizer.tools.fetch_channel import get_fetch_channel_tool
from mattermost_summarizer.tools.fetch_thread import get_fetch_thread_tool
from mattermost_summarizer.tools.finish import get_finish_tool
from mattermost_summarizer.tools.get_user import get_get_user_tool

if TYPE_CHECKING:
    from mattermost_summarizer.client import MattermostClient


def build_mattermost_tools(client: MattermostClient) -> Sequence[Tool]:
    """Build all Mattermost tools for the agent.

    Args:
        client: MattermostClient instance to use for API calls

    Returns:
        Sequence of Tool spec instances (registered with the SDK)
    """
    tools: list[Tool] = [
        get_fetch_thread_tool(client),
        get_get_user_tool(client),
        get_fetch_channel_tool(client),
        get_finish_tool(),
    ]
    return tools


__all__ = [
    "build_mattermost_tools",
    "get_fetch_thread_tool",
    "get_get_user_tool",
    "get_fetch_channel_tool",
    "get_finish_tool",
]
