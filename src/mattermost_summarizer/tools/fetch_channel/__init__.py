"""FetchChannel tool - retrieves a Mattermost channel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mattermost_summarizer.tools.fetch_channel.impl import (
    FetchChannelAction,
    FetchChannelExecutor,
    FetchChannelObservation,
    FetchChannelTool,
)

if TYPE_CHECKING:
    from openhands.sdk import Tool

    from mattermost_summarizer.client import MattermostClient


_registered: bool = False


def get_fetch_channel_tool(client: MattermostClient) -> Tool:
    global _registered
    from openhands.sdk import Tool as _Tool  # pyright: ignore[reportUnknownVariableType]
    from openhands.sdk import register_tool  # pyright: ignore[reportUnknownVariableType]

    if not _registered:
        instance = FetchChannelTool.create(client=client)[0]
        register_tool("fetch_channel", instance)
        _registered = True

    return _Tool(name="fetch_channel", params={})


__all__ = [
    "FetchChannelAction",
    "FetchChannelExecutor",
    "FetchChannelObservation",
    "FetchChannelTool",
    "get_fetch_channel_tool",
]
