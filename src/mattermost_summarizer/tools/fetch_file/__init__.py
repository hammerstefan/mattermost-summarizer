"""FetchFile tool - retrieves a Mattermost file attachment."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mattermost_summarizer.tools.fetch_file.impl import (
    FetchFileAction,
    FetchFileExecutor,
    FetchFileObservation,
    FetchFileTool,
)

if TYPE_CHECKING:
    from openhands.sdk import Tool

    from mattermost_summarizer.client import MattermostClient


_registered: bool = False


def get_fetch_file_tool(client: MattermostClient) -> Tool:
    global _registered
    from openhands.sdk import Tool as _Tool  # pyright: ignore[reportUnknownVariableType]
    from openhands.sdk import register_tool  # pyright: ignore[reportUnknownVariableType]

    if not _registered:
        instance = FetchFileTool.create(client=client)[0]
        register_tool("fetch_file", instance)
        _registered = True

    return _Tool(name="fetch_file", params={})


__all__ = [
    "FetchFileAction",
    "FetchFileExecutor",
    "FetchFileObservation",
    "FetchFileTool",
    "get_fetch_file_tool",
]
