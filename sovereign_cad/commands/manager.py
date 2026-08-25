﻿from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import Command, CommandResult


@dataclass
class CommandManager:
    """
    Executes commands and maintains undo/redo history.
    """

    context: Any = None
    undo_stack: list[Command] = field(default_factory=list)
    redo_stack: list[Command] = field(default_factory=list)

    def execute(self, command: Command) -> CommandResult:
        result = command.execute(self.context)

        if result.success:
            self.undo_stack.append(command)
            self.redo_stack.clear()

        return result

    def undo(self) -> CommandResult:
        if not self.undo_stack:
            return CommandResult(
                success=False,
                message="Nothing to undo.",
            )

        command = self.undo_stack.pop()
        result = command.undo(self.context)

        if result.success:
            self.redo_stack.append(command)
        else:
            self.undo_stack.append(command)

        return result

    def redo(self) -> CommandResult:
        if not self.redo_stack:
            return CommandResult(
                success=False,
                message="Nothing to redo.",
            )

        command = self.redo_stack.pop()
        result = command.execute(self.context)

        if result.success:
            self.undo_stack.append(command)
        else:
            self.redo_stack.append(command)

        return result

    def clear(self) -> None:
        self.undo_stack.clear()
        self.redo_stack.clear()

    @property
    def can_undo(self) -> bool:
        return bool(self.undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self.redo_stack)
