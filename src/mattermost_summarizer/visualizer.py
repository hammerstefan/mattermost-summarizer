from __future__ import annotations

from pathlib import Path

from openhands.sdk.conversation.visualizer.default import (
    DefaultConversationVisualizer,
)
from rich.console import Console


class FileConversationVisualizer(DefaultConversationVisualizer):
    """Writes Rich-formatted agent trace output to a file instead of stdout."""

    def __init__(self, log_file: str | Path = "agent-trace.log") -> None:
        self._log_path = Path(log_file)
        self._file = open(self._log_path, "a", encoding="utf-8")
        console = Console(
            file=self._file,
            force_terminal=True,
            width=120,
        )
        super().__init__()
        self._console = console

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()

    def __enter__(self) -> FileConversationVisualizer:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


__all__ = ["FileConversationVisualizer"]
