"""Data models for mattermost-summarizer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PostData(BaseModel):
    """A single post in a Mattermost thread."""

    id: str
    author_id: str
    author_username: str | None = None
    author_display_name: str | None = None
    message: str
    created_at: datetime
    reply_count: int = 0
    reactions: list[ReactionData] = []
    attachments: list[str] = []
    props: dict[str, Any] = {}


class ReactionData(BaseModel):
    """A reaction to a post."""

    user_id: str
    emoji_name: str
    create_at: datetime


class PostThread(BaseModel):
    """A complete thread (root post + replies)."""

    root: PostData
    replies: list[PostData] = []
    channel_id: str
    channel_name: str | None = None
    total_replies: int = 0


class UserProfile(BaseModel):
    """A Mattermost user profile."""

    id: str
    username: str
    display_name: str
    email: str | None = None
    nickname: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class Channel(BaseModel):
    """A Mattermost channel."""

    id: str
    name: str
    display_name: str
    purpose: str | None = None
    header: str | None = None
    team_name: str | None = None
    type: str = "O"  # O=public, P=private, D=direct, G=group


class SummaryMeta(BaseModel):
    """Metadata about a summary operation."""

    thread_length: int = 0
    cost: float = 0.0
    model_used: str = ""
    duration_seconds: float = 0.0


class SummaryResult(BaseModel):
    """Result of summarizing a Mattermost thread."""

    tldr: str
    narrative: str
    action_items: list[str] = []
    participants: list[str] = []
    metadata: SummaryMeta = SummaryMeta()

    def __str__(self) -> str:
        """Pretty format the summary result."""
        lines = [
            "=" * 70,
            "TL;DR",
            "=" * 70,
            self.tldr,
            "",
            "=" * 70,
            "NARRATIVE",
            "=" * 70,
            self.narrative,
        ]

        if self.action_items:
            lines.extend(
                [
                    "",
                    "=" * 70,
                    "ACTION ITEMS",
                    "=" * 70,
                ]
            )
            for item in self.action_items:
                lines.append(f"  • {item}")

        if self.participants:
            lines.extend(
                [
                    "",
                    "=" * 70,
                    "PARTICIPANTS",
                    "=" * 70,
                    ", ".join(self.participants),
                ]
            )

        lines.extend(
            [
                "",
                "=" * 70,
                "METADATA",
                "=" * 70,
                f"  Thread length: {self.metadata.thread_length} posts",
                f"  LLM cost: ${self.metadata.cost:.4f}",
                f"  Model: {self.metadata.model_used}",
                f"  Duration: {self.metadata.duration_seconds:.1f}s",
            ]
        )

        return "\n".join(lines)
