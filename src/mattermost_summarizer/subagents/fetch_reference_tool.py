"""Fetch reference tool for orchestrator (consolidates tracking and delegation)."""

from __future__ import annotations

import itertools
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from openhands.sdk import Action, Observation
from openhands.sdk.llm.message import TextContent
from openhands.sdk.tool import ToolExecutor
from openhands.sdk.tool.tool import ToolDefinition

if TYPE_CHECKING:
    from mattermost_summarizer.tools.reference_tracker import ReferenceTracker

logger = logging.getLogger(__name__)


class FetchReferenceAction(Action):
    """Action to safely fetch a reference URL."""

    url: str


class FetchReferenceObservation(Observation):
    """Observation from fetching a reference."""

    result: str
    error: str | None = None

    @property
    def to_llm_content(self) -> Sequence[TextContent]:
        if self.error:
            return [TextContent(text=f"Error: {self.error}")]
        return [TextContent(text=self.result)]


class FetchReferenceExecutor(ToolExecutor[FetchReferenceAction, FetchReferenceObservation]):
    """Executor for fetching references (handles cycle tracking + sub-agent delegation)."""

    def __init__(self, tracker: ReferenceTracker | None = None) -> None:
        from mattermost_summarizer.tools.reference_tracker import ReferenceTracker

        self._tracker = tracker or ReferenceTracker()

        # We instantiate a DelegateExecutor to handle the sub-agent interaction
        from openhands.tools.delegate.impl import DelegateExecutor

        self._delegate_executor = DelegateExecutor()
        self._agent_counter = itertools.count()

    def __call__(self, action: FetchReferenceAction, conversation: object | None = None) -> FetchReferenceObservation:
        if not action.url:
            return FetchReferenceObservation(result="", error="URL required")

        from mattermost_summarizer.tools.reference_tracker import classify_url_full, ReferenceType

        # Classify first to fail-fast on unknown URLs (Point 4)
        classified = classify_url_full(action.url)
        if classified.reference_type == ReferenceType.UNKNOWN:
            return FetchReferenceObservation(result="", error="Unsupported URL type. Cannot follow.")

        # Check cyclic/depth tracking (Point 2)
        with self._tracker.lock():
            if self._tracker.has_been_followed(action.url):
                return FetchReferenceObservation(result="", error="URL has already been followed (cycle prevented).")
            if not self._tracker.can_follow_deeper():
                return FetchReferenceObservation(
                    result="", error=f"Maximum reference depth ({self._tracker.max_depth}) reached."
                )

            # Mark followed. Only increment depth for follow-on references —
            # the initial root fetch does not consume a depth slot, so that
            # max_depth=3 allows 3 levels of references rather than 2.
            is_root_fetch = len(self._tracker.followed_urls) == 0
            self._tracker.mark_followed(action.url)
            if not is_root_fetch:
                self._tracker.increment_depth()

        # Spawn the appropriate sub-agent with a unique ID to avoid clobbering
        # a previous sub-agent of the same type still registered in DelegateExecutor._sub_agents.
        from openhands.tools.delegate.definition import DelegateAction

        agent_id = f"subagent_{classified.agent_type}_{next(self._agent_counter)}"

        spawn_action = DelegateAction(command="spawn", ids=[agent_id], agent_types=[classified.agent_type])
        # Execute spawn (we ignore the output unless it's an error)
        spawn_obs = self._delegate_executor(spawn_action, conversation)  # type: ignore
        if getattr(spawn_obs, "is_error", False):
            # Rollback tracking just in case
            return FetchReferenceObservation(
                result="", error=f"Failed to spawn sub-agent: {spawn_obs.to_llm_content[0].text}"
            )

        # Delegate the task to the spawned agent
        task_desc = (
            f"Fetch and summarize this reference: {action.url}\n"
            "Return the full relevant content, any attachments/links, "
            "and highlight important patches/logs/context."
        )
        delegate_action = DelegateAction(command="delegate", tasks={agent_id: task_desc})
        delegate_obs = self._delegate_executor(delegate_action, conversation)  # type: ignore

        result_text = "\n".join(c.text for c in delegate_obs.to_llm_content if hasattr(c, "text"))
        return FetchReferenceObservation(result=result_text)


class FetchReferenceTool(ToolDefinition[FetchReferenceAction, FetchReferenceObservation]):
    """Tool for fetching a reference URL, safely handling depth/cycle tracking."""

    name = "fetch_reference"

    @classmethod
    def create(cls, tracker: ReferenceTracker | None = None, **kwargs: object) -> Sequence[FetchReferenceTool]:
        return [
            cls(
                description=(
                    "Fetch a reference URL. "
                    "Automatically checks if the URL was already followed to prevent cycles, "
                    "verifies depth limits, and delegates to the appropriate sub-agent to fetch the content. "
                    "Returns the summarized content of the reference, or an error if it cannot be followed."
                ),
                action_type=FetchReferenceAction,
                observation_type=FetchReferenceObservation,
                executor=FetchReferenceExecutor(tracker),
            )
        ]


__all__ = [
    "FetchReferenceTool",
    "FetchReferenceAction",
    "FetchReferenceObservation",
    "FetchReferenceExecutor",
]
