"""finish tool - signals the agent has completed summarization."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mattermost_summarizer.tools.finish.definition import (
    SummarizerFinishAction,
    SummarizerFinishExecutor,
    SummarizerFinishObservation,
    SummarizerFinishTool,
)

if TYPE_CHECKING:
    from openhands.sdk import Tool


_registered: bool = False


def get_finish_tool() -> Tool:
    global _registered
    from openhands.sdk import Tool as _Tool  # pyright: ignore[reportUnknownVariableType]
    from openhands.sdk import register_tool  # pyright: ignore[reportUnknownVariableType]

    if not _registered:
        instance = SummarizerFinishTool.create()[0]
        register_tool("finish", instance)
        _registered = True

    return _Tool(name="finish", params={})


__all__ = [
    "SummarizerFinishAction",
    "SummarizerFinishExecutor",
    "SummarizerFinishObservation",
    "SummarizerFinishTool",
    "get_finish_tool",
]
