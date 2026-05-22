"""FetchLaunchpadBug tool - retrieves a public Launchpad bug."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mattermost_summarizer.tools.fetch_launchpad_bug.impl import (
    FetchLaunchpadBugAction,
    FetchLaunchpadBugExecutor,
    FetchLaunchpadBugObservation,
    FetchLaunchpadBugTool,
)

if TYPE_CHECKING:
    from openhands.sdk import Tool


_registered: bool = False


def get_fetch_launchpad_bug_tool() -> Tool:
    global _registered
    from openhands.sdk import Tool as _Tool  # pyright: ignore[reportUnknownVariableType]
    from openhands.sdk import register_tool  # pyright: ignore[reportUnknownVariableType]

    if not _registered:
        instance = FetchLaunchpadBugTool.create()[0]
        register_tool("fetch_launchpad_bug", instance)
        _registered = True

    return _Tool(name="fetch_launchpad_bug", params={})


__all__ = [
    "FetchLaunchpadBugAction",
    "FetchLaunchpadBugExecutor",
    "FetchLaunchpadBugObservation",
    "FetchLaunchpadBugTool",
    "get_fetch_launchpad_bug_tool",
]
