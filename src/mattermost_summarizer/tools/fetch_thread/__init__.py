"""FetchThread tool - retrieves a Mattermost thread."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mattermost_summarizer.tools.fetch_thread.impl import (
    FetchThreadAction,
    FetchThreadExecutor,
    FetchThreadObservation,
    FetchThreadTool,
)

if TYPE_CHECKING:
    from openhands.sdk import Tool

    from mattermost_summarizer.client import MattermostClient


_registered: bool = False


def get_fetch_thread_tool(client: MattermostClient) -> Tool:
    global _registered
    from openhands.sdk import Tool as _Tool  # pyright: ignore[reportUnknownVariableType]
    from openhands.sdk import register_tool  # pyright: ignore[reportUnknownVariableType]

    if not _registered:
        instance = FetchThreadTool.create(client=client)[0]
        register_tool("fetch_thread", instance)
        _registered = True

    return _Tool(name="fetch_thread", params={})


__all__ = [
    "FetchThreadAction",
    "FetchThreadExecutor",
    "FetchThreadObservation",
    "FetchThreadTool",
    "get_fetch_thread_tool",
]
