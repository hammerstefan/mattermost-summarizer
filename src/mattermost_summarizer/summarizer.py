"""Main summarizer module for mattermost-summarizer."""

from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path

from openhands.sdk import LocalConversation
from openhands.sdk.event.llm_convertible.observation import ObservationEvent
from openhands.tools.delegate.definition import DelegateObservation

from mattermost_summarizer.agent import build_orchestrator_agent
from mattermost_summarizer.client import MattermostClient
from mattermost_summarizer.config import MattermostSummarizerConfig
from mattermost_summarizer.critic import SummarizationCritic
from mattermost_summarizer.exceptions import (
    AgentStuckError,
    PermalinkError,
)
from mattermost_summarizer.levels import (
    AnySummaryResult,
    BriefSummaryResult,
    DetailedSummaryResult,
    NormalSummaryResult,
    SummarizerFinishActionBase,
    SummaryLevel,
    SummaryMeta,
)
from mattermost_summarizer.subagents import register_subagents
from mattermost_summarizer.tools.reference_tracker import (
    ClassifiedUrl,
    ReferenceTracker,
    classify_urls_in_text,
)
from mattermost_summarizer.utils import parse_permalink
from mattermost_summarizer.visualizer import FileConversationVisualizer


class MattermostSummarizer:
    """High-level API for summarizing Mattermost conversation threads.

    Example usage:
        summarizer = MattermostSummarizer.from_config("mattermost-summarizer.toml")
        result = summarizer.summarize("https://chat.canonical.com/canonical/pl/abc123xyz")
        print(result)

    Or with environment variables:
        summarizer = MattermostSummarizer.from_env()
        result = summarizer.summarize("https://chat.example.com/team/pl/post123")
        print(result.tldr)
    """

    def __init__(self, config: MattermostSummarizerConfig) -> None:
        self.config = config

    @classmethod
    def from_config(cls, path: Path | str) -> MattermostSummarizer:
        """Load configuration from a TOML file.

        Args:
            path: Path to TOML config file

        Returns:
            MattermostSummarizer instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ConfigError: If config is invalid
        """
        config = MattermostSummarizerConfig.from_config(path)
        return cls(config)

    @classmethod
    def from_env(cls) -> MattermostSummarizer:
        """Load configuration from environment variables.

        Returns:
            MattermostSummarizer instance
        """
        config = MattermostSummarizerConfig.from_env()
        return cls(config)

    def summarize(
        self,
        permalink_url: str,
        level: SummaryLevel = SummaryLevel.NORMAL,
    ) -> AnySummaryResult:
        """Summarize a Mattermost thread from a permalink URL.

        Args:
            permalink_url: A Mattermost permalink (e.g., https://chat.example.com/team/pl/abc123)
            level: Summarization detail level (default: NORMAL)

        Returns:
            AnySummaryResult (BriefSummaryResult, NormalSummaryResult, or DetailedSummaryResult)
                with tldr, narrative (if not brief), action_items, participants (if not brief), and metadata

        Raises:
            PermalinkError: If URL format is invalid
            AuthenticationError: If Mattermost API returns 401
            ThreadNotFoundError: If thread doesn't exist (404)
            AgentStuckError: If agent gets stuck and cannot complete
        """
        start_time = time.time()

        try:
            post_id = parse_permalink(permalink_url)
        except ValueError as e:
            raise PermalinkError(str(e)) from e

        message = f"Summarize this Mattermost thread: {permalink_url}\nThe post ID is: {post_id}"

        visualizer = FileConversationVisualizer("agent-trace.log")

        with (
            MattermostClient(
                base_url=str(self.config.mattermost_url),
                token=self.config.mattermost_token.get_secret_value(),
            ) as client,
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            register_subagents(client)

            critic = None
            if self.config.critic_enabled:
                critic = SummarizationCritic(
                    llm_model=self.config.llm_model,
                    llm_api_key=self.config.llm_api_key.get_secret_value(),
                    llm_base_url=self.config.llm_base_url,
                    level=level,
                )

            tracker = ReferenceTracker(max_depth=self.config.max_reference_depth)

            agent = build_orchestrator_agent(
                llm_model=self.config.llm_model,
                llm_api_key=self.config.llm_api_key.get_secret_value(),
                llm_base_url=self.config.llm_base_url,
                level=level,
                max_reference_depth=self.config.max_reference_depth,
                critic=critic,
                tracker=tracker,
            )

            conv_ref: list[LocalConversation | None] = [None]
            finish_seen_ref = [False]

            def _on_finish_callback(event: object) -> None:
                if (
                    not finish_seen_ref[0]
                    and hasattr(event, "action")
                    and isinstance(getattr(event, "action", None), SummarizerFinishActionBase)
                    and conv_ref[0] is not None
                ):
                    finish_seen_ref[0] = True
                    conv_ref[0].pause()

            pause_callback = _make_pause_after_delegation_callback(conv_ref)

            conversation = LocalConversation(
                agent=agent,
                workspace=tmpdir,
                visualizer=visualizer,
                callbacks=[_on_finish_callback, pause_callback.callback],
            )
            conv_ref[0] = conversation

            conversation.send_message(message)  # type: ignore[arg-type, misc]

            _MAX_DELEGATION_ITERATIONS = 20
            for _iteration in range(_MAX_DELEGATION_ITERATIONS):
                if finish_seen_ref[0]:
                    break
                pause_callback.reset()
                conversation.run()  # type: ignore[misc]

                if finish_seen_ref[0]:
                    break

                delegate_text = _extract_last_delegate_observation(conversation)
                if not delegate_text:
                    # No delegation observed — orchestrator went straight to finish or
                    # something unexpected occurred; exit the loop.
                    break

                classified_urls = classify_urls_in_text(delegate_text, tracker)

                if classified_urls:
                    url_message = format_url_injection_message(classified_urls, tracker)
                    if url_message:
                        conversation.send_message(url_message)  # type: ignore[arg-type, misc]
                # If no classified_urls: no message injected; loop continues and run()
                # will let the orchestrator proceed to synthesize and call finish.
            else:
                logging.getLogger(__name__).warning(
                    "Summarization loop reached max iterations (%d) without finishing.",
                    _MAX_DELEGATION_ITERATIONS,
                )

            try:
                finish_action = _extract_finish_action(conversation)

                if finish_action is None:
                    if conversation.stuck_detector and conversation.stuck_detector.is_stuck():
                        raise AgentStuckError(
                            "Agent got stuck and could not complete the summarization. "
                            "This may be due to repeated actions or context issues."
                        )
                    raise AgentStuckError("Agent did not produce a finish action. The summary could not be extracted.")

                duration = time.time() - start_time

                cost = 0.0
                input_tokens = 0
                output_tokens = 0
                cache_read_tokens = 0
                cache_write_tokens = 0
                reasoning_tokens = 0

                if hasattr(agent.llm, "metrics") and agent.llm.metrics:
                    cost = getattr(agent.llm.metrics, "accumulated_cost", 0.0)
                    token_usage = getattr(agent.llm.metrics, "accumulated_token_usage", None)
                    if token_usage:
                        input_tokens = (
                            getattr(token_usage, "prompt_tokens", 0) or getattr(token_usage, "input_tokens", 0) or 0
                        )
                        output_tokens = (
                            getattr(token_usage, "completion_tokens", 0)
                            or getattr(token_usage, "output_tokens", 0)
                            or 0
                        )
                        cache_read_tokens = getattr(token_usage, "cache_read_tokens", 0) or 0
                        cache_write_tokens = getattr(token_usage, "cache_write_tokens", 0) or 0
                        reasoning_tokens = getattr(token_usage, "reasoning_tokens", 0) or 0

                thread_length = 1
                if hasattr(finish_action, "tldr"):
                    thread_length = _estimate_thread_length(conversation)

                metadata = SummaryMeta(
                    thread_length=thread_length,
                    cost=cost,
                    model_used=self.config.llm_model,
                    duration_seconds=duration,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_read_tokens=cache_read_tokens,
                    cache_write_tokens=cache_write_tokens,
                    reasoning_tokens=reasoning_tokens,
                )

                tldr = getattr(finish_action, "tldr", "")
                action_items = getattr(finish_action, "action_items", [])
                key_findings = getattr(finish_action, "key_findings", [])
                narrative = getattr(finish_action, "narrative", "")
                participants = getattr(finish_action, "participants", [])

                if level == SummaryLevel.BRIEF:
                    return BriefSummaryResult(
                        tldr=tldr,
                        action_items=action_items,
                        metadata=metadata,
                    )
                elif level == SummaryLevel.DETAILED:
                    return DetailedSummaryResult(
                        tldr=tldr,
                        key_findings=key_findings,
                        narrative=narrative,
                        action_items=action_items,
                        participants=participants,
                        open_questions=getattr(finish_action, "open_questions", []),
                        context_sources=getattr(finish_action, "context_sources", []),
                        metadata=metadata,
                    )
                else:
                    return NormalSummaryResult(
                        tldr=tldr,
                        key_findings=key_findings,
                        narrative=narrative,
                        action_items=action_items,
                        participants=participants,
                        metadata=metadata,
                    )
            finally:
                conversation.close()
                visualizer.close()


class _PauseAfterDelegationCallback:
    """Factory-produced callback that pauses `run()` on the first delegate-command DelegateObservation.

    Usage::

        cb = _make_pause_after_delegation_callback(conv_ref)
        conversation = LocalConversation(..., callbacks=[..., cb.callback])
        # Before each conv.run() call:
        cb.reset()
        conversation.run()
    """

    def __init__(self, conv_ref: list[LocalConversation | None]) -> None:
        self._conv_ref = conv_ref
        self._fired = False

    def reset(self) -> None:
        """Re-arm the callback for the next run() segment."""
        self._fired = False

    def callback(self, event: object) -> None:
        if self._fired:
            return
        if not isinstance(event, ObservationEvent):
            return
        if not isinstance(event.observation, DelegateObservation):
            return
        if event.observation.command != "delegate":
            return
        self._fired = True
        conv = self._conv_ref[0]
        if conv is not None:
            conv.pause()


def _make_pause_after_delegation_callback(
    conv_ref: list[LocalConversation | None],
) -> _PauseAfterDelegationCallback:
    """Create a pause-after-delegation callback bound to *conv_ref*.

    The callback fires exactly once per run() segment (re-armed via ``reset()``).
    It fires only on ``DelegateObservation`` events where ``command == "delegate"``,
    ignoring spawn observations and all other event types.
    """
    return _PauseAfterDelegationCallback(conv_ref)


def _extract_finish_action(conversation: LocalConversation) -> SummarizerFinishActionBase | None:
    """Scan conversation events for a SummarizerFinishAction."""
    if not hasattr(conversation, "state") or not conversation.state:
        return None

    events = getattr(conversation.state, "events", [])

    for event in reversed(events):
        if hasattr(event, "action") and event.action is not None:
            action = event.action
            if isinstance(action, SummarizerFinishActionBase):
                return action

        if hasattr(event, "observation") and event.observation is not None:
            obs = event.observation
            if hasattr(obs, "success") and hasattr(obs, "summary_provided"):
                if obs.summary_provided:
                    for prev_event in reversed(events):
                        if hasattr(prev_event, "action") and prev_event.action is not None:
                            prev_action = prev_event.action
                            if isinstance(prev_action, SummarizerFinishActionBase):
                                return prev_action

    return None


def _estimate_thread_length(conversation: LocalConversation) -> int:
    """Estimate the number of posts in the thread from conversation events."""
    fetch_count = 0

    if hasattr(conversation, "state") and conversation.state:
        events = getattr(conversation.state, "events", [])
        for event in events:
            if hasattr(event, "action") and event.action is not None:
                action = event.action
                if hasattr(action, "post_id"):
                    fetch_count += 1

            if hasattr(event, "observation") and event.observation is not None:
                obs = event.observation
                if hasattr(obs, "total_replies"):
                    return int(obs.total_replies) + 1

    return fetch_count + 1


def _extract_last_delegate_observation(conversation: LocalConversation) -> str | None:
    """Extract text from the most recent delegate-command DelegateObservation.

    Scans conversation.state.events in reverse for the most recent
    ObservationEvent where observation is a DelegateObservation with
    command == "delegate".
    """
    if not hasattr(conversation, "state") or not conversation.state:
        return None

    events = getattr(conversation.state, "events", [])

    for event in reversed(events):
        if isinstance(event, ObservationEvent):
            if isinstance(event.observation, DelegateObservation):
                if event.observation.command == "delegate":
                    text_parts: list[str] = []
                    for c in event.observation.to_llm_content:
                        if hasattr(c, "text"):
                            text_parts.append(c.text)
                    return "".join(text_parts)

    return None


def format_url_injection_message(
    classified_urls: list[ClassifiedUrl],
    tracker: ReferenceTracker,
) -> str:
    """Format the classified URL list as an injected user message."""
    if not classified_urls:
        return ""

    lines: list[str] = ["References found in delegation result:"]
    for i, ref in enumerate(classified_urls, 1):
        lines.append(f"{i}. {ref.url}  ({ref.reference_type.value} -> {ref.agent_type})")

    depth_status = "can follow more" if tracker.can_follow_deeper() else "max depth reached"
    lines.append(f"URLs followed: {tracker.current_depth}/{tracker.max_depth} — {depth_status}")
    lines.append("")
    lines.append("Decide which (if any) are relevant and call follow_url before delegating.")

    return "\n".join(lines)
