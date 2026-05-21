"""finish tool - signals the agent has completed summarization."""

from collections.abc import Sequence

from openhands.sdk import Action, Observation, TextContent
from openhands.sdk.tool import ToolExecutor
from openhands.sdk.tool.tool import ToolAnnotations, ToolDefinition
from pydantic import Field


class FinishAction(Action):
    """Signal that summarization is complete with the final summary.

    This tool should be called when the agent has gathered all necessary
    information and produced a complete summary of the Mattermost thread.
    """

    tldr: str = Field(description="Bullet-point TL;DR of the conversation (3-5 key points)")
    narrative: str = Field(description="Chronological narrative of the conversation, noting who said what")
    action_items: list[str] = Field(
        default_factory=list, description="Decisions, todos, follow-ups, or assignments mentioned"
    )
    participants: list[str] = Field(default_factory=list, description="People who contributed to the thread")


class FinishObservation(Observation):
    """Result of the finish action."""

    success: bool = True
    summary_provided: bool = True

    @property
    def to_llm_content(self) -> Sequence[TextContent]:
        return [TextContent(text="Summary complete. Thank you!")]


class FinishExecutor(ToolExecutor[FinishAction, FinishObservation]):
    """Executor for the finish tool.

    This is a terminal action - the real work happens in summarizer.py
    which extracts the FinishAction from conversation events.
    """

    def __call__(self, action: FinishAction, conversation: object | None = None) -> FinishObservation:
        return FinishObservation(success=True, summary_provided=True)


class FinishTool(ToolDefinition[FinishAction, FinishObservation]):
    """Tool for signaling the completion of a summarization task."""

    @classmethod
    def create(cls, conv_state: object | None = None, **kwargs: object) -> Sequence["FinishTool"]:
        """Create FinishTool instance.

        Args:
            conv_state: Optional conversation state (not used by this tool)
            **kwargs: Additional parameters (none supported)

        Returns:
            A sequence containing a single FinishTool instance
        """
        return [
            cls(
                description=(
                    "Call this tool when you have completed the summarization. "
                    "This tool accepts the final summary in structured form: "
                    "TL;DR (3-5 bullet points), narrative (chronological story), "
                    "action items (decisions/follow-ups), and participants list. "
                    "Always provide substantive content for all fields."
                ),
                action_type=FinishAction,
                observation_type=FinishObservation,
                executor=FinishExecutor(),
                annotations=ToolAnnotations(
                    title="finish",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            )
        ]


__all__ = ["FinishAction", "FinishObservation", "FinishExecutor", "FinishTool"]
