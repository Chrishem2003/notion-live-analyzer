from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CommandResult:
    success: bool
    message: str = ""
    data: Any = None


class Command(ABC):
    """
    Base class for reversible application commands.

    Commands execute against an application/document context and
    may provide an undo operation.
    """

    name: str = "Command"

    @abstractmethod
    def execute(self, context: Any) -> CommandResult:
        raise NotImplementedError

    def undo(self, context: Any) -> CommandResult:
        return CommandResult(
            success=False,
            message=f"{self.name} does not support undo.",
        )
