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
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0


def _format_token_count(value: int) -> str:
    """Format a token count with K suffix for >= 1000."""
    if value >= 1000:
        return f"{value / 1000:.2f}K"
    return str(value)


class SummaryResult(BaseModel):
    """Result of summarizing a Mattermost thread."""

    tldr: str
    key_findings: list[str] = []
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
        ]

        if self.key_findings:
            lines.extend(
                [
                    "",
                    "=" * 70,
                    "KEY FINDINGS",
                    "=" * 70,
                ]
            )
            for finding in self.key_findings:
                lines.append(f"  • {finding}")

        lines.extend(
            [
                "",
                "=" * 70,
                "NARRATIVE",
                "=" * 70,
                self.narrative,
            ]
        )

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
                f"  Model: {self.metadata.model_used}",
                f"  Duration: {self.metadata.duration_seconds:.1f}s",
            ]
        )

        tokens_parts = [f"↑ input {_format_token_count(self.metadata.input_tokens)}"]

        cache_read = self.metadata.cache_read_tokens
        input_with_cache = self.metadata.input_tokens + cache_read
        if input_with_cache > 0 and cache_read > 0:
            cache_hit_pct = (cache_read / input_with_cache) * 100
            tokens_parts.append(f"cache hit {cache_hit_pct:.2f}%")

        if self.metadata.reasoning_tokens > 0:
            tokens_parts.append(f"reasoning {self.metadata.reasoning_tokens}")

        tokens_parts.append(f"↓ output {_format_token_count(self.metadata.output_tokens)}")
        tokens_parts.append(f"$ {self.metadata.cost:.2f}")

        lines.append(f"  Tokens: {' • '.join(tokens_parts)}")

        return "\n".join(lines)
