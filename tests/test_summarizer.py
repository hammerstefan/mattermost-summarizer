"""Tests for summarizer.py - _on_finish_callback and _extract_finish_action."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from mattermost_summarizer.levels import (
    BriefFinishAction,
    DetailedFinishAction,
    NormalFinishAction,
    SummarizerFinishActionBase,
)
from mattermost_summarizer.summarizer import (
    _PauseAfterDelegationCallback,
    _extract_finish_action,
    _extract_last_delegate_observation,
    _make_pause_after_delegation_callback,
)


class MockEvent:
    def __init__(self, action: Any | None = None, observation: Any | None = None) -> None:
        self.action: Any | None = action
        self.observation: Any | None = observation


class MockConversationState:
    def __init__(self, events: list[MockEvent]) -> None:
        self._events: list[MockEvent] = events

    @property
    def events(self) -> list[MockEvent]:
        return self._events


class MockConversation:
    def __init__(self, events: list[MockEvent], stuck_detector: Any | None = None) -> None:
        self.state: MockConversationState = MockConversationState(events)
        self._paused: bool = False
        self._stuck_detector: Any | None = stuck_detector

    @property
    def stuck_detector(self) -> Any | None:
        return self._stuck_detector

    def pause(self) -> None:
        self._paused = True


class MockStuckDetector:
    def __init__(self, is_stuck_value: bool = False) -> None:
        self._is_stuck: bool = is_stuck_value

    def is_stuck(self) -> bool:
        return self._is_stuck


class TestOnFinishCallback:
    """Tests for the _on_finish_callback closure inside summarize()."""

    def _build_callback(self):
        conv_ref: list[MockConversation | None] = [None]
        finish_seen_ref: list[bool] = [False]

        def _on_finish_callback(event: MockEvent) -> None:
            if (
                not finish_seen_ref[0]
                and hasattr(event, "action")
                and isinstance(getattr(event, "action", None), SummarizerFinishActionBase)
                and conv_ref[0] is not None
            ):
                finish_seen_ref[0] = True
                conv_ref[0].pause()

        return _on_finish_callback, conv_ref, finish_seen_ref

    def test_callback_triggers_on_brief_finish_action(self) -> None:
        callback, conv_ref, _ = self._build_callback()
        conv = MockConversation([])
        conv_ref[0] = conv

        event = MockEvent(action=BriefFinishAction(tldr="- Point", action_items=[]))
        callback(event)

        assert conv._paused is True

    def test_callback_triggers_on_normal_finish_action(self) -> None:
        callback, conv_ref, _ = self._build_callback()
        conv = MockConversation([])
        conv_ref[0] = conv

        event = MockEvent(
            action=NormalFinishAction(
                tldr="- Point",
                narrative="Story",
                action_items=[],
                participants=[],
            )
        )
        callback(event)

        assert conv._paused is True

    def test_callback_triggers_on_detailed_finish_action(self) -> None:
        callback, conv_ref, _ = self._build_callback()
        conv = MockConversation([])
        conv_ref[0] = conv

        event = MockEvent(
            action=DetailedFinishAction(
                tldr="- Point",
                narrative="Story",
                action_items=[],
                participants=[],
                open_questions=[],
                context_sources=[],
            )
        )
        callback(event)

        assert conv._paused is True

    def test_callback_ignores_non_finish_action(self) -> None:
        callback, conv_ref, _ = self._build_callback()
        conv = MockConversation([])
        conv_ref[0] = conv

        class SomeOtherAction:
            pass

        event = MockEvent(action=SomeOtherAction())
        callback(event)

        assert conv._paused is False

    def test_callback_ignores_event_with_no_action(self) -> None:
        callback, conv_ref, _ = self._build_callback()
        conv = MockConversation([])
        conv_ref[0] = conv

        event = MockEvent(action=None)
        callback(event)

        assert conv._paused is False

    def test_callback_only_pauses_once(self) -> None:
        callback, conv_ref, finish_seen_ref = self._build_callback()
        conv = MockConversation([])
        conv_ref[0] = conv

        event1 = MockEvent(action=BriefFinishAction(tldr="- First", action_items=[]))
        callback(event1)
        assert conv._paused is True
        assert finish_seen_ref[0] is True

        conv._paused = False
        event2 = MockEvent(
            action=NormalFinishAction(
                tldr="- Second",
                narrative="Story",
                action_items=[],
                participants=[],
            )
        )
        callback(event2)
        assert conv._paused is False

    def test_callback_does_nothing_when_conv_not_set(self) -> None:
        callback, conv_ref, _ = self._build_callback()
        conv_ref[0] = None

        event = MockEvent(action=BriefFinishAction(tldr="- Point", action_items=[]))
        callback(event)


class TestExtractFinishAction:
    """Tests for _extract_finish_action()."""

    def test_extract_returns_none_when_no_events(self) -> None:
        conv = MockConversation([])
        result = _extract_finish_action(conv)
        assert result is None

    def test_extract_returns_none_when_no_state(self) -> None:
        from unittest.mock import MagicMock

        conv = MagicMock(spec=[])
        conv.state = None
        result = _extract_finish_action(conv)
        assert result is None

    def test_extract_finds_brief_finish_action(self) -> None:
        action = BriefFinishAction(tldr="- Point", action_items=[])
        events = [MockEvent(action=action)]
        conv = MockConversation(events)

        result = _extract_finish_action(conv)
        assert result is action

    def test_extract_finds_normal_finish_action(self) -> None:
        action = NormalFinishAction(
            tldr="- Point",
            narrative="Story",
            action_items=[],
            participants=[],
        )
        events = [MockEvent(action=action)]
        conv = MockConversation(events)

        result = _extract_finish_action(conv)
        assert result is action

    def test_extract_finds_detailed_finish_action(self) -> None:
        action = DetailedFinishAction(
            tldr="- Point",
            narrative="Story",
            action_items=[],
            participants=[],
            open_questions=[],
            context_sources=[],
        )
        events = [MockEvent(action=action)]
        conv = MockConversation(events)

        result = _extract_finish_action(conv)
        assert result is action

    def test_extract_returns_last_finish_action_in_reverse_order(self) -> None:
        action1 = BriefFinishAction(tldr="- First", action_items=[])
        action2 = NormalFinishAction(
            tldr="- Second",
            narrative="Story",
            action_items=[],
            participants=[],
        )
        events = [MockEvent(action=action1), MockEvent(action=action2)]
        conv = MockConversation(events)

        result = _extract_finish_action(conv)
        assert result is action2

    def test_extract_skips_non_finish_actions(self) -> None:
        class SomeOtherAction:
            pass

        action = NormalFinishAction(
            tldr="- Point",
            narrative="Story",
            action_items=[],
            participants=[],
        )
        events = [
            MockEvent(action=SomeOtherAction()),
            MockEvent(action=SomeOtherAction()),
            MockEvent(action=action),
        ]
        conv = MockConversation(events)

        result = _extract_finish_action(conv)
        assert result is action

    def test_extract_returns_none_for_empty_events(self) -> None:
        conv = MockConversation([])
        result = _extract_finish_action(conv)
        assert result is None


class TestSummarizerFinishActionBaseIsinstance:
    """Verify that all level actions are instances of SummarizerFinishActionBase."""

    def test_brief_finish_action_isinstance(self) -> None:
        action = BriefFinishAction(tldr="- Point", action_items=[])
        assert isinstance(action, SummarizerFinishActionBase)

    def test_normal_finish_action_isinstance(self) -> None:
        action = NormalFinishAction(
            tldr="- Point",
            narrative="Story",
            action_items=[],
            participants=[],
        )
        assert isinstance(action, SummarizerFinishActionBase)

    def test_detailed_finish_action_isinstance(self) -> None:
        action = DetailedFinishAction(
            tldr="- Point",
            narrative="Story",
            action_items=[],
            participants=[],
            open_questions=[],
            context_sources=[],
        )
        assert isinstance(action, SummarizerFinishActionBase)

    def test_is_summarizer_finish_sentinel(self) -> None:
        action = BriefFinishAction(tldr="- Point", action_items=[])
        assert action.is_summarizer_finish is True

        action2 = DetailedFinishAction(
            tldr="- Point",
            narrative="Story",
            action_items=[],
            participants=[],
            open_questions=[],
            context_sources=[],
        )
        assert action2.is_summarizer_finish is True


# ---------------------------------------------------------------------------
# Helpers shared by the pause-callback and extract-delegate tests
# ---------------------------------------------------------------------------


class _FakeDelegateObservation:
    """Minimal stand-in for DelegateObservation."""

    def __init__(self, command: str, content_text: str = "") -> None:
        self.command = command
        self._text = content_text

    @property
    def to_llm_content(self) -> list[Any]:
        class _TextContent:
            def __init__(self, text: str) -> None:
                self.text = text

        return [_TextContent(self._text)] if self._text else []


class _FakeObservationEvent:
    """Minimal stand-in for ObservationEvent with a DelegateObservation."""

    def __init__(self, observation: Any) -> None:
        self.observation = observation


class _FakeOtherObservation:
    """Any non-DelegateObservation."""

    pass


class _FakeActionEvent:
    """Event with an action attribute but no observation."""

    def __init__(self, action: Any = None) -> None:
        self.action = action


# ---------------------------------------------------------------------------
# Tests for _PauseAfterDelegationCallback / _make_pause_after_delegation_callback
# ---------------------------------------------------------------------------


class TestPauseAfterDelegationCallback:
    """Tests for _PauseAfterDelegationCallback (task 4.3)."""

    def _make(self) -> tuple[_PauseAfterDelegationCallback, MagicMock, list]:
        """Return (callback, mock_conv, conv_ref)."""
        mock_conv = MagicMock()
        mock_conv.pause = MagicMock()
        conv_ref: list[Any] = [mock_conv]
        cb = _make_pause_after_delegation_callback(conv_ref)
        return cb, mock_conv, conv_ref

    def _make_delegate_event(self, command: str = "delegate") -> _FakeObservationEvent:
        obs = _FakeDelegateObservation(command=command)
        return _FakeObservationEvent(obs)

    def _patch_isinstance(self):
        """Patch isinstance checks in summarizer so our fakes pass them."""
        import mattermost_summarizer.summarizer as mod

        obs_event_patch = patch.object(mod, "ObservationEvent", _FakeObservationEvent)
        delegate_obs_patch = patch.object(mod, "DelegateObservation", _FakeDelegateObservation)
        return obs_event_patch, delegate_obs_patch

    def test_fires_on_delegate_command(self) -> None:
        cb, mock_conv, _ = self._make()
        p1, p2 = self._patch_isinstance()
        with p1, p2:
            cb.callback(self._make_delegate_event("delegate"))
        mock_conv.pause.assert_called_once()

    def test_does_not_fire_on_spawn_command(self) -> None:
        cb, mock_conv, _ = self._make()
        p1, p2 = self._patch_isinstance()
        with p1, p2:
            cb.callback(self._make_delegate_event("spawn"))
        mock_conv.pause.assert_not_called()

    def test_does_not_fire_on_non_observation_event(self) -> None:
        cb, mock_conv, _ = self._make()
        p1, p2 = self._patch_isinstance()
        with p1, p2:
            cb.callback(_FakeActionEvent())
        mock_conv.pause.assert_not_called()

    def test_does_not_fire_on_non_delegate_observation(self) -> None:
        cb, mock_conv, _ = self._make()
        p1, p2 = self._patch_isinstance()
        other_obs = _FakeOtherObservation()
        with p1, p2:
            cb.callback(_FakeObservationEvent(other_obs))
        mock_conv.pause.assert_not_called()

    def test_fires_only_once_per_segment(self) -> None:
        cb, mock_conv, _ = self._make()
        p1, p2 = self._patch_isinstance()
        with p1, p2:
            cb.callback(self._make_delegate_event("delegate"))
            cb.callback(self._make_delegate_event("delegate"))  # second call — must be no-op
        assert mock_conv.pause.call_count == 1

    def test_reset_rearms_callback(self) -> None:
        cb, mock_conv, _ = self._make()
        p1, p2 = self._patch_isinstance()
        with p1, p2:
            cb.callback(self._make_delegate_event("delegate"))
            cb.reset()
            cb.callback(self._make_delegate_event("delegate"))  # re-armed — must fire again
        assert mock_conv.pause.call_count == 2

    def test_does_nothing_when_conv_ref_is_none(self) -> None:
        cb = _make_pause_after_delegation_callback([None])
        p1, p2 = self._patch_isinstance()
        with p1, p2:
            # Must not raise even when conv_ref[0] is None
            cb.callback(self._make_delegate_event("delegate"))


# ---------------------------------------------------------------------------
# Tests for _extract_last_delegate_observation
# ---------------------------------------------------------------------------


class TestExtractLastDelegateObservation:
    """Tests for _extract_last_delegate_observation() (task 4.4)."""

    def _conv(self, events: list[Any]) -> MagicMock:
        conv = MagicMock()
        conv.state = MagicMock()
        conv.state.events = events
        return conv

    def _patch_isinstance(self):
        import mattermost_summarizer.summarizer as mod

        obs_event_patch = patch.object(mod, "ObservationEvent", _FakeObservationEvent)
        delegate_obs_patch = patch.object(mod, "DelegateObservation", _FakeDelegateObservation)
        return obs_event_patch, delegate_obs_patch

    def _obs_event(self, command: str = "delegate", text: str = "") -> _FakeObservationEvent:
        return _FakeObservationEvent(_FakeDelegateObservation(command=command, content_text=text))

    def test_returns_none_when_no_events(self) -> None:
        p1, p2 = self._patch_isinstance()
        with p1, p2:
            result = _extract_last_delegate_observation(self._conv([]))
        assert result is None

    def test_returns_none_when_no_state(self) -> None:
        conv = MagicMock()
        conv.state = None
        p1, p2 = self._patch_isinstance()
        with p1, p2:
            result = _extract_last_delegate_observation(conv)
        assert result is None

    def test_returns_text_from_delegate_observation(self) -> None:
        events = [self._obs_event("delegate", "thread content here")]
        p1, p2 = self._patch_isinstance()
        with p1, p2:
            result = _extract_last_delegate_observation(self._conv(events))
        assert result == "thread content here"

    def test_ignores_spawn_observations(self) -> None:
        events = [self._obs_event("spawn", "spawn text")]
        p1, p2 = self._patch_isinstance()
        with p1, p2:
            result = _extract_last_delegate_observation(self._conv(events))
        assert result is None

    def test_returns_most_recent_delegate_observation(self) -> None:
        events = [
            self._obs_event("delegate", "first"),
            self._obs_event("delegate", "second"),
        ]
        p1, p2 = self._patch_isinstance()
        with p1, p2:
            result = _extract_last_delegate_observation(self._conv(events))
        assert result == "second"

    def test_skips_non_observation_events(self) -> None:
        events = [
            _FakeActionEvent(),
            self._obs_event("delegate", "found"),
        ]
        p1, p2 = self._patch_isinstance()
        with p1, p2:
            result = _extract_last_delegate_observation(self._conv(events))
        assert result == "found"

    def test_uses_hasattr_not_type_check_for_text(self) -> None:
        """Content items without a .text attribute are silently skipped."""

        class _NoText:
            pass

        class _WithText:
            text = "hello"

        class _OddObservation(_FakeDelegateObservation):
            @property
            def to_llm_content(self) -> list[Any]:
                return [_NoText(), _WithText()]

        events = [_FakeObservationEvent(_OddObservation("delegate"))]
        p1, p2 = self._patch_isinstance()
        with p1, p2:
            result = _extract_last_delegate_observation(self._conv(events))
        assert result == "hello"
