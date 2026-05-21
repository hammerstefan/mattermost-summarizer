"""FetchThread tool - retrieves a Mattermost thread."""

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

from mattermost_summarizer.exceptions import AuthenticationError, ThreadNotFoundError


class FetchThreadAction(Action):
    """Fetch a Mattermost thread by root post ID."""

    post_id: str = Field(description="Root post ID of the thread to fetch")


class FetchThreadObservation(Observation):
    """Result of fetching a thread."""

    root_post: dict[str, object]
    replies: list[dict[str, object]]
    channel_id: str
    channel_name: str | None
    total_replies: int
    error: str | None = None

    @property
    def to_llm_content(self) -> Sequence[TextContent]:
        if self.error:
            return [TextContent(text=f"Error fetching thread: {self.error}")]

        lines: list[str] = []

        channel_info = f" in #{self.channel_name}" if self.channel_name else ""
        lines.append(f"Thread{channel_info}")
        lines.append("=" * 50)

        root = self.root_post
        root_author = root.get("author_name", root.get("author_id", "Unknown"))
        root_time = root.get("created_at", "unknown time")
        root_msg = root.get("message", "")
        lines.append(f"Root post by @{root_author} at {root_time}:")
        lines.append(f"  {root_msg}")
        lines.append("")

        if self.total_replies > 0:
            lines.append(f"--- Replies ({self.total_replies}) ---")
            for i, reply in enumerate(self.replies, 1):
                author = reply.get("author_name", reply.get("author_id", "Unknown"))
                time = reply.get("created_at", "unknown time")
                msg = reply.get("message", "")
                lines.append(f"{i}. @{author} at {time}:")
                lines.append(f"   {msg}")
                lines.append("")
        else:
            lines.append("--- No replies ---")

        return [TextContent(text="\n".join(lines))]


class FetchThreadExecutor(ToolExecutor[FetchThreadAction, FetchThreadObservation]):
    """Executor for fetching Mattermost threads."""

    def __init__(self, client: MattermostClient | None) -> None:
        self.client = client

    def __call__(self, action: FetchThreadAction, conversation: object | None = None) -> FetchThreadObservation:
        if self.client is None:
            raise ValueError("Client not provided")
        try:
            thread = self.client.get_post_thread(action.post_id)

            all_user_ids = {thread.root.author_id}
            for reply in thread.replies:
                all_user_ids.add(reply.author_id)

            user_cache: dict[str, str] = {}
            for user_id in all_user_ids:
                if user_id:
                    try:
                        user = self.client.get_user(user_id)
                        user_cache[user_id] = user.username
                    except Exception:
                        user_cache[user_id] = user_id

            root_post: dict[str, object] = {
                "id": thread.root.id,
                "author_id": thread.root.author_id,
                "author_name": user_cache.get(thread.root.author_id, thread.root.author_id),
                "message": thread.root.message,
                "created_at": thread.root.created_at.isoformat() if thread.root.created_at else "",
                "reply_count": thread.root.reply_count,
            }

            replies_data: list[dict[str, object]] = []
            for reply in thread.replies:
                replies_data.append(
                    {
                        "id": reply.id,
                        "author_id": reply.author_id,
                        "author_name": user_cache.get(reply.author_id, reply.author_id),
                        "message": reply.message,
                        "created_at": reply.created_at.isoformat() if reply.created_at else "",
                        "reply_count": reply.reply_count,
                    }
                )

            return FetchThreadObservation(
                root_post=root_post,
                replies=replies_data,
                channel_id=thread.channel_id,
                channel_name=thread.channel_name,
                total_replies=thread.total_replies,
                error=None,
            )
        except (AuthenticationError, ThreadNotFoundError, httpx.HTTPError) as e:
            return FetchThreadObservation(
                root_post={},
                replies=[],
                channel_id="",
                channel_name=None,
                total_replies=0,
                error=str(e),
            )


class FetchThreadTool(ToolDefinition[FetchThreadAction, FetchThreadObservation]):
    """Tool for fetching a Mattermost thread by root post ID."""

    @classmethod
    def create(cls, client: MattermostClient | None = None, **kwargs: object) -> Sequence[FetchThreadTool]:
        """Create FetchThreadTool instance.

        Args:
            client: MattermostClient instance for API calls
            **kwargs: Additional parameters (none supported)

        Returns:
            A sequence containing a single FetchThreadTool instance
        """
        return [
            cls(
                description=(
                    "Fetch a complete Mattermost thread given the root post ID. "
                    "Returns the root post and all replies, formatted for easy reading. "
                    "Use this first to understand the conversation before summarizing."
                ),
                action_type=FetchThreadAction,
                observation_type=FetchThreadObservation,
                executor=FetchThreadExecutor(client),
                annotations=ToolAnnotations(
                    title="fetch_thread",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            )
        ]


__all__ = [
    "FetchThreadAction",
    "FetchThreadObservation",
    "FetchThreadExecutor",
    "FetchThreadTool",
]
