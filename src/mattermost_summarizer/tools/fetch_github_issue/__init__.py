"""FetchGitHubIssue tool - retrieves a GitHub issue or pull request."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mattermost_summarizer.tools.fetch_github_issue.impl import (
    FetchGitHubIssueAction,
    FetchGitHubIssueExecutor,
    FetchGitHubIssueObservation,
    FetchGitHubIssueTool,
)

if TYPE_CHECKING:
    from openhands.sdk import Tool as Tool  # pyright: ignore[reportUnknownVariableType]
    from pydantic import SecretStr


_registered: bool = False


def get_fetch_github_issue_tool(github_token: SecretStr | None = None) -> Tool:
    global _registered
    from openhands.sdk import Tool as _Tool  # pyright: ignore[reportUnknownVariableType]
    from openhands.sdk import register_tool  # pyright: ignore[reportUnknownVariableType]

    if not _registered:
        instance = FetchGitHubIssueTool.create(github_token=github_token)[0]
        register_tool("fetch_github_issue", instance)
        _registered = True

    return _Tool(name="fetch_github_issue", params={})


__all__ = [
    "FetchGitHubIssueAction",
    "FetchGitHubIssueExecutor",
    "FetchGitHubIssueObservation",
    "FetchGitHubIssueTool",
    "get_fetch_github_issue_tool",
]
