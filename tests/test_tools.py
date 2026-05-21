"""Tests for OpenHands tools."""


class TestFinishTool:
    def test_finish_observation_to_llm_content(self) -> None:
        from mattermost_summarizer.tools.finish.definition import (
            SummarizerFinishObservation,
        )

        obs = SummarizerFinishObservation(success=True, summary_provided=True)
        content = obs.to_llm_content
        assert len(content) == 1
        assert "Summary complete" in content[0].text


class TestFetchThreadTool:
    def test_fetch_thread_observation_format(self) -> None:
        from mattermost_summarizer.tools.fetch_thread.impl import (
            FetchThreadObservation,
        )

        obs = FetchThreadObservation(
            root_post={
                "id": "root123",
                "author_name": "alice",
                "message": "Hello everyone!",
                "created_at": "2026-05-21T10:00:00",
            },
            replies=[
                {
                    "id": "reply1",
                    "author_name": "bob",
                    "message": "Hi alice!",
                    "created_at": "2026-05-21T10:05:00",
                }
            ],
            channel_id="channel1",
            channel_name="general",
            total_replies=1,
        )

        content = obs.to_llm_content
        assert len(content) == 1
        text = content[0].text
        assert "Thread" in text
        assert "general" in text
        assert "alice" in text
        assert "Hello everyone" in text
        assert "bob" in text
        assert "Hi alice" in text

    def test_fetch_thread_observation_error(self) -> None:
        from mattermost_summarizer.tools.fetch_thread.impl import (
            FetchThreadObservation,
        )

        obs = FetchThreadObservation(
            root_post={},
            replies=[],
            channel_id="",
            channel_name=None,
            total_replies=0,
            error="Connection failed",
        )

        content = obs.to_llm_content
        assert "Error" in content[0].text


class TestGetUserTool:
    def test_get_user_observation_format(self) -> None:
        from mattermost_summarizer.tools.get_user.impl import GetUserObservation

        obs = GetUserObservation(
            user_id="user123",
            username="jdoe",
            display_name="Jane Doe",
            email="jane@example.com",
        )

        content = obs.to_llm_content
        assert len(content) == 1
        text = content[0].text
        assert "@jdoe" in text
        assert "Jane Doe" in text

    def test_get_user_observation_error(self) -> None:
        from mattermost_summarizer.tools.get_user.impl import GetUserObservation

        obs = GetUserObservation(
            user_id="user123",
            username="",
            display_name="",
            error="User not found",
        )

        content = obs.to_llm_content
        assert "Error" in content[0].text


class TestFetchChannelTool:
    def test_fetch_channel_observation_format(self) -> None:
        from mattermost_summarizer.tools.fetch_channel.impl import (
            FetchChannelObservation,
        )

        obs = FetchChannelObservation(
            channel_id="channel123",
            name="general",
            display_name="General",
            purpose="Company-wide discussion",
            team_name="myteam",
        )

        content = obs.to_llm_content
        assert len(content) == 1
        text = content[0].text
        assert "#General" in text
        assert "myteam" in text
        assert "Company-wide" in text

    def test_fetch_channel_observation_error(self) -> None:
        from mattermost_summarizer.tools.fetch_channel.impl import (
            FetchChannelObservation,
        )

        obs = FetchChannelObservation(
            channel_id="invalid",
            name="",
            display_name="",
            error="Channel not found",
        )

        content = obs.to_llm_content
        assert "Error" in content[0].text
