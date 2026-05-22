"""Delegate tool for multi-agent orchestration."""

from __future__ import annotations

from collections.abc import Sequence

from openhands.sdk.tool.tool import ToolDefinition


class DelegateTool(ToolDefinition["DelegateAction", "DelegateObservation"]):  # type: ignore[valid-type,name-defined]
    name = "delegate"

    @classmethod
    def create(cls, **kwargs: object) -> Sequence[DelegateTool]:
        from openhands.tools.delegate.definition import (
            DelegateAction,
            DelegateObservation,
        )
        from openhands.tools.delegate.impl import DelegateExecutor

        return [
            cls(
                description=(
                    "Delegate tasks to sub-agents by name. Use command 'delegate' with agent_types "
                    "list and tasks dictionary. Example: agent_types=['thread_fetcher'], "
                    "tasks={'thread_fetcher': 'Fetch thread abc123'}"
                ),
                action_type=DelegateAction,
                observation_type=DelegateObservation,
                executor=DelegateExecutor(),
                annotations=None,  # type: ignore[arg-type]
            )
        ]


def register_delegate_tool() -> None:
    from openhands.sdk import register_tool  # pyright: ignore

    register_tool("delegate", DelegateTool)
