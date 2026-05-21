"""GetUser tool - retrieves a Mattermost user profile."""

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

from mattermost_summarizer.exceptions import AuthenticationError, UserNotFoundError


class GetUserAction(Action):
    """Fetch a Mattermost user profile by ID."""

    user_id: str = Field(description="User ID to look up")


class GetUserObservation(Observation):
    """Result of fetching a user profile."""

    user_id: str
    username: str
    display_name: str
    email: str | None = None
    nickname: str | None = None
    error: str | None = None

    @property
    def to_llm_content(self) -> Sequence[TextContent]:
        if self.error:
            return [TextContent(text=f"Error fetching user: {self.error}")]

        name = self.display_name or self.nickname or self.username
        return [TextContent(text=f"@{self.username} ({name})")]


class GetUserExecutor(ToolExecutor[GetUserAction, GetUserObservation]):
    """Executor for fetching Mattermost user profiles."""

    def __init__(self, client: MattermostClient | None) -> None:
        self.client = client

    def __call__(self, action: GetUserAction, conversation: object | None = None) -> GetUserObservation:
        if self.client is None:
            raise ValueError("Client not provided")
        try:
            user = self.client.get_user(action.user_id)
            return GetUserObservation(
                user_id=user.id,
                username=user.username,
                display_name=user.display_name,
                email=user.email,
                nickname=user.nickname,
                error=None,
            )
        except (AuthenticationError, UserNotFoundError, httpx.HTTPError) as e:
            return GetUserObservation(
                user_id=action.user_id,
                username="",
                display_name="",
                email=None,
                nickname=None,
                error=str(e),
            )


class GetUserTool(ToolDefinition[GetUserAction, GetUserObservation]):
    """Tool for fetching a Mattermost user profile by ID."""

    @classmethod
    def create(cls, client: MattermostClient | None = None, **kwargs: object) -> Sequence[GetUserTool]:
        """Create GetUserTool instance.

        Args:
            client: MattermostClient instance for API calls
            **kwargs: Additional parameters (none supported)

        Returns:
            A sequence containing a single GetUserTool instance
        """
        return [
            cls(
                description=(
                    "Fetch a Mattermost user profile to resolve user IDs to names. "
                    "Use this when you need more details about a specific user mentioned in a thread."
                ),
                action_type=GetUserAction,
                observation_type=GetUserObservation,
                executor=GetUserExecutor(client),
                annotations=ToolAnnotations(
                    title="get_user",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            )
        ]


__all__ = [
    "GetUserAction",
    "GetUserExecutor",
    "GetUserObservation",
    "GetUserTool",
]
