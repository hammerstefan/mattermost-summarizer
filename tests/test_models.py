"""Tests for data models."""

from datetime import datetime

from mattermost_summarizer.models import (
    Channel,
    PostData,
    PostThread,
    SummaryMeta,
    SummaryResult,
    UserProfile,
)


class TestPostData:
    def test_create_post_data(self) -> None:
        post = PostData(
            id="post123",
            author_id="user456",
            author_username="jdoe",
            author_display_name="Jane Doe",
            message="Hello, world!",
            created_at=datetime(2026, 5, 21, 10, 0, 0),
            reply_count=5,
        )
        assert post.id == "post123"
        assert post.author_id == "user456"
        assert post.author_username == "jdoe"
        assert post.message == "Hello, world!"

    def test_post_data_defaults(self) -> None:
        post = PostData(
            id="post123",
            author_id="user456",
            message="Test",
            created_at=datetime.now(),
        )
        assert post.reply_count == 0
        assert post.reactions == []
        assert post.attachments == []
        assert post.props == {}


class TestUserProfile:
    def test_create_user_profile(self) -> None:
        user = UserProfile(
            id="user123",
            username="jdoe",
            display_name="Jane Doe",
            email="jane@example.com",
        )
        assert user.id == "user123"
        assert user.username == "jdoe"
        assert user.display_name == "Jane Doe"
        assert user.email == "jane@example.com"

    def test_user_profile_optional_fields(self) -> None:
        user = UserProfile(
            id="user123",
            username="jdoe",
            display_name="Jane Doe",
        )
        assert user.email is None
        assert user.nickname is None


class TestChannel:
    def test_create_channel(self) -> None:
        channel = Channel(
            id="channel123",
            name="general",
            display_name="General",
            purpose="Company-wide announcements",
            type="O",
        )
        assert channel.id == "channel123"
        assert channel.name == "general"
        assert channel.type == "O"

    def test_channel_types(self) -> None:
        public_channel = Channel(id="1", name="public", display_name="Public", type="O")
        private_channel = Channel(id="2", name="private", display_name="Private", type="P")
        assert public_channel.type == "O"
        assert private_channel.type == "P"


class TestSummaryResult:
    def test_create_summary_result(self) -> None:
        result = SummaryResult(
            tldr="- Item 1\n- Item 2",
            narrative="Once upon a time...",
            action_items=["Do this", "Do that"],
            participants=["Alice", "Bob"],
            metadata=SummaryMeta(
                thread_length=10,
                cost=0.05,
                model_used="openai/gpt-4o",
                duration_seconds=3.5,
            ),
        )
        assert "Item 1" in result.tldr
        assert "Alice" in result.participants
        assert result.metadata.thread_length == 10

    def test_summary_result_str_format(self) -> None:
        result = SummaryResult(
            tldr="- Key point",
            narrative="The story goes...",
            action_items=["Action 1"],
            participants=["Alice"],
            metadata=SummaryMeta(
                thread_length=5,
                cost=0.02,
                model_used="test-model",
                duration_seconds=1.0,
            ),
        )
        output = str(result)
        assert "TL;DR" in output
        assert "NARRATIVE" in output
        assert "ACTION ITEMS" in output
        assert "PARTICIPANTS" in output
        assert "METADATA" in output
        assert "Alice" in output
        assert "Tokens:" in output
        assert "LLM cost:" not in output

    def test_tokens_format_with_k_suffix(self) -> None:
        result = SummaryResult(
            tldr="- Key point",
            narrative="The story goes...",
            participants=["Alice"],
            metadata=SummaryMeta(
                thread_length=5,
                cost=0.0042,
                model_used="test-model",
                duration_seconds=1.0,
                input_tokens=35690,
                output_tokens=1820,
                cache_read_tokens=1000,
                cache_write_tokens=0,
                reasoning_tokens=653,
            ),
        )
        output = str(result)
        assert "35.69K" in output
        assert "1.82K" in output
        assert "653" in output

    def test_tokens_format_with_small_counts(self) -> None:
        result = SummaryResult(
            tldr="- Key point",
            narrative="The story goes...",
            participants=["Alice"],
            metadata=SummaryMeta(
                thread_length=5,
                cost=0.0001,
                model_used="test-model",
                duration_seconds=1.0,
                input_tokens=500,
                output_tokens=500,
                cache_read_tokens=0,
                cache_write_tokens=0,
                reasoning_tokens=0,
            ),
        )
        output = str(result)
        assert "Tokens: ↑ input 500 • ↓ output 500 • $ 0.00" in output
        assert "cache hit" not in output
        assert "reasoning" not in output

    def test_tokens_omit_zero_cache_hit_and_reasoning(self) -> None:
        result = SummaryResult(
            tldr="- Key point",
            narrative="The story goes...",
            participants=["Alice"],
            metadata=SummaryMeta(
                thread_length=5,
                cost=0.00,
                model_used="test-model",
                duration_seconds=1.0,
                input_tokens=500,
                output_tokens=500,
                cache_read_tokens=0,
                cache_write_tokens=0,
                reasoning_tokens=0,
            ),
        )
        output = str(result)
        assert "cache hit" not in output
        assert "reasoning" not in output


class TestPostThread:
    def test_create_post_thread(self) -> None:
        root = PostData(
            id="root123",
            author_id="user1",
            message="Root post",
            created_at=datetime(2026, 5, 21, 9, 0, 0),
        )
        reply = PostData(
            id="reply456",
            author_id="user2",
            message="A reply",
            created_at=datetime(2026, 5, 21, 9, 5, 0),
        )
        thread = PostThread(
            root=root,
            replies=[reply],
            channel_id="channel123",
            channel_name="general",
            total_replies=1,
        )
        assert thread.root.id == "root123"
        assert len(thread.replies) == 1
        assert thread.channel_name == "general"

    def test_post_thread_empty_replies(self) -> None:
        root = PostData(
            id="root123",
            author_id="user1",
            message="Single post",
            created_at=datetime.now(),
        )
        thread = PostThread(
            root=root,
            replies=[],
            channel_id="channel123",
            total_replies=0,
        )
        assert thread.total_replies == 0
        assert thread.replies == []
