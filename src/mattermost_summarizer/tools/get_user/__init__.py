"""GetUser tool - retrieves a Mattermost user profile."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mattermost_summarizer.tools.get_user.impl import (
    GetUserAction,
    GetUserExecutor,
    GetUserObservation,
    GetUserTool,
)

if TYPE_CHECKING:
    from openhands.sdk import Tool

    from mattermost_summarizer.client import MattermostClient


_registered: bool = False


def get_get_user_tool(client: MattermostClient) -> Tool:
    global _registered
    from openhands.sdk import Tool as _Tool  # pyright: ignore[reportUnknownVariableType]
    from openhands.sdk import register_tool  # pyright: ignore[reportUnknownVariableType]

    if not _registered:
        instance = GetUserTool.create(client=client)[0]
        register_tool("get_user", instance)
        _registered = True

    return _Tool(name="get_user", params={})


__all__ = [
    "GetUserAction",
    "GetUserExecutor",
    "GetUserObservation",
    "GetUserTool",
    "get_get_user_tool",
]
