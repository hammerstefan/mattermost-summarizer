"""FetchChannel tool - retrieves a Mattermost channel."""

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

from mattermost_summarizer.exceptions import AuthenticationError, ChannelNotFoundError


class FetchChannelAction(Action):
    """Fetch a Mattermost channel by ID."""

    channel_id: str = Field(description="Channel ID to look up")


class FetchChannelObservation(Observation):
    """Result of fetching a channel."""

    channel_id: str
    name: str
    display_name: str
    purpose: str | None = None
    header: str | None = None
    team_name: str | None = None
    error: str | None = None

    @property
    def to_llm_content(self) -> Sequence[TextContent]:
        if self.error:
            return [TextContent(text=f"Error fetching channel: {self.error}")]

        lines = [f"Channel: #{self.display_name}"]

        if self.team_name:
            lines.append(f"Team: {self.team_name}")

        if self.purpose:
            lines.append(f"Purpose: {self.purpose}")

        if self.header:
            lines.append(f"Header: {self.header}")

        return [TextContent(text="\n".join(lines))]


class FetchChannelExecutor(ToolExecutor[FetchChannelAction, FetchChannelObservation]):
    """Executor for fetching Mattermost channels."""

    def __init__(self, client: MattermostClient | None) -> None:
        self.client = client

    def __call__(self, action: FetchChannelAction, conversation: object | None = None) -> FetchChannelObservation:
        if self.client is None:
            raise ValueError("Client not provided")
        try:
            channel = self.client.get_channel(action.channel_id)
            return FetchChannelObservation(
                channel_id=channel.id,
                name=channel.name,
                display_name=channel.display_name,
                purpose=channel.purpose,
                header=channel.header,
                team_name=channel.team_name,
                error=None,
            )
        except (AuthenticationError, ChannelNotFoundError, httpx.HTTPError) as e:
            return FetchChannelObservation(
                channel_id=action.channel_id,
                name="",
                display_name="",
                purpose=None,
                header=None,
                team_name=None,
                error=str(e),
            )


class FetchChannelTool(ToolDefinition[FetchChannelAction, FetchChannelObservation]):
    """Tool for fetching a Mattermost channel by ID."""

    @classmethod
    def create(cls, client: MattermostClient | None = None, **kwargs: object) -> Sequence[FetchChannelTool]:
        """Create FetchChannelTool instance.

        Args:
            client: MattermostClient instance for API calls
            **kwargs: Additional parameters (none supported)

        Returns:
            A sequence containing a single FetchChannelTool instance
        """
        return [
            cls(
                description=(
                    "Fetch a Mattermost channel to get context about where a thread is located. "
                    "Returns channel name, purpose, and team information. "
                    "Use this when you need more context about a thread."
                ),
                action_type=FetchChannelAction,
                observation_type=FetchChannelObservation,
                executor=FetchChannelExecutor(client),
                annotations=ToolAnnotations(
                    title="fetch_channel",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            )
        ]


__all__ = [
    "FetchChannelAction",
    "FetchChannelExecutor",
    "FetchChannelObservation",
    "FetchChannelTool",
]
