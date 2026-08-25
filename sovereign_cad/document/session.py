from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sovereign_cad.commands import CommandManager


@dataclass
class DocumentSession:
    """
    Runtime application session connecting the document registry
    and command system.
    """

    registry: Any = None
    command_manager: CommandManager = field(init=False)

    active_tool: str | None = None

    def __post_init__(self) -> None:
        self.command_manager = CommandManager(
            context=self
        )

    def execute(self, command) -> Any:
        return self.command_manager.execute(command)

    def undo(self) -> Any:
        return self.command_manager.undo()

    def redo(self) -> Any:
        return self.command_manager.redo()

    def set_tool(self, tool_name: str | None) -> None:
        self.active_tool = tool_name

    def clear_tool(self) -> None:
        self.active_tool = None
