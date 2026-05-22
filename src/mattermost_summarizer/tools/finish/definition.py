"""finish tool - signals the agent has completed summarization."""

from collections.abc import Sequence

from openhands.sdk import Action, Observation, TextContent
from openhands.sdk.tool import ToolExecutor
from openhands.sdk.tool.tool import ToolAnnotations, ToolDefinition
from pydantic import Field


class SummarizerFinishAction(Action):
    """Signal that summarization is complete with the final summary.

    This tool should be called when the agent has gathered all necessary
    information and produced a complete summary of the Mattermost thread.
    """

    tldr: str = Field(description="Bullet-point TL;DR of the conversation (3-5 key points)")
    key_findings: list[str] = Field(
        default_factory=list, description="Key findings or insights discovered in the conversation"
    )
    narrative: str = Field(description="Chronological narrative of the conversation, noting who said what")
    action_items: list[str] = Field(
        default_factory=list, description="Decisions, todos, follow-ups, or assignments mentioned"
    )
    participants: list[str] = Field(default_factory=list, description="People who contributed to the thread")


class SummarizerFinishObservation(Observation):
    """Result of the finish action."""

    success: bool = True
    summary_provided: bool = True

    @property
    def to_llm_content(self) -> Sequence[TextContent]:
        return [TextContent(text="Summary complete. Thank you!")]


class SummarizerFinishExecutor(ToolExecutor[SummarizerFinishAction, SummarizerFinishObservation]):
    """Executor for the finish tool.

    This is a terminal action - the real work happens in summarizer.py
    which extracts the SummarizerFinishAction from conversation events.
    """

    def __call__(
        self, action: SummarizerFinishAction, conversation: object | None = None
    ) -> SummarizerFinishObservation:
        return SummarizerFinishObservation(success=True, summary_provided=True)


class SummarizerFinishTool(ToolDefinition[SummarizerFinishAction, SummarizerFinishObservation]):
    """Tool for signaling the completion of a summarization task."""

    name = "finish"  # Override so the SDK recognizes this as terminal

    @classmethod
    def create(cls, conv_state: object | None = None, **kwargs: object) -> Sequence["SummarizerFinishTool"]:
        """Create SummarizerFinishTool instance.

        Args:
            conv_state: Optional conversation state (not used by this tool)
            **kwargs: Additional parameters (none supported)

        Returns:
            A sequence containing a single SummarizerFinishTool instance
        """
        return [
            cls(
                description=(
                    "Call this tool when you have completed the summarization. "
                    "This tool accepts the final summary in structured form: "
                    "TL;DR (3-5 bullet points), key findings (insights/discoveries), "
                    "narrative (chronological story), "
                    "action items (decisions/follow-ups), and participants list. "
                    "Always provide substantive content for all fields."
                ),
                action_type=SummarizerFinishAction,
                observation_type=SummarizerFinishObservation,
                executor=SummarizerFinishExecutor(),
                annotations=ToolAnnotations(
                    title="finish",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            )
        ]


__all__ = ["SummarizerFinishAction", "SummarizerFinishObservation", "SummarizerFinishExecutor", "SummarizerFinishTool"]
