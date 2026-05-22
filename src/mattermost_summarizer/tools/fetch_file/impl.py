"""FetchFile tool - retrieves a Mattermost file attachment."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import httpx
from openhands.sdk import Action, Observation, TextContent
from openhands.sdk.tool import ToolExecutor
from openhands.sdk.tool.tool import ToolAnnotations, ToolDefinition
from pydantic import Field

if TYPE_CHECKING:
    from mattermost_summarizer.client import MattermostClient

from mattermost_summarizer.exceptions import AuthenticationError, FileNotFoundError, ThreadNotFoundError


class FetchFileAction(Action):
    """Fetch a Mattermost file attachment by file ID."""

    file_id: str = Field(description="File ID of the attachment to fetch")


class FetchFileObservation(Observation):
    """Result of fetching a file."""

    file_text_content: str | None = None
    is_binary: bool = False
    mime_type: str | None = None
    error: str | None = None

    @property
    def to_llm_content(self) -> Sequence[TextContent]:
        if self.error:
            return [TextContent(text=f"Error fetching file: {self.error}")]

        if self.is_binary:
            return [TextContent(text=f"Binary file ({self.mime_type}): not readable as text")]

        return [TextContent(text=self.file_text_content or "")]


class FetchFileExecutor(ToolExecutor[FetchFileAction, FetchFileObservation]):
    """Executor for fetching Mattermost file attachments."""

    def __init__(self, client: MattermostClient | None) -> None:
        self.client = client

    def __call__(self, action: FetchFileAction, conversation: object | None = None) -> FetchFileObservation:
        if self.client is None:
            raise ValueError("Client not provided")
        try:
            content, content_type = self.client.get_file(action.file_id)

            if content_type.startswith("text/") or content_type == "application/json":
                try:
                    text_content = content.decode("utf-8")
                    return FetchFileObservation(
                        file_text_content=text_content,
                        is_binary=False,
                        mime_type=content_type,
                        error=None,
                    )
                except UnicodeDecodeError:
                    pass

            return FetchFileObservation(
                file_text_content=None,
                is_binary=True,
                mime_type=content_type,
                error=None,
            )
        except (AuthenticationError, FileNotFoundError, ThreadNotFoundError, httpx.HTTPError) as e:
            return FetchFileObservation(
                file_text_content=None,
                is_binary=False,
                mime_type=None,
                error=str(e),
            )


class FetchFileTool(ToolDefinition[FetchFileAction, FetchFileObservation]):
    """Tool for fetching a Mattermost file attachment by file ID."""

    @classmethod
    def create(cls, client: MattermostClient | None = None, **kwargs: object) -> Sequence[FetchFileTool]:
        """Create FetchFileTool instance.

        Args:
            client: MattermostClient instance for API calls
            **kwargs: Additional parameters (none supported)

        Returns:
            A sequence containing a single FetchFileTool instance
        """
        return [
            cls(
                description=(
                    "Fetch a Mattermost file attachment by file ID. "
                    "Returns the file content as plain text for text-based files, "
                    "or a 'not readable' signal for binary files."
                ),
                action_type=FetchFileAction,
                observation_type=FetchFileObservation,
                executor=FetchFileExecutor(client),
                annotations=ToolAnnotations(
                    title="fetch_file",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            )
        ]


__all__ = [
    "FetchFileAction",
    "FetchFileExecutor",
    "FetchFileObservation",
    "FetchFileTool",
]
