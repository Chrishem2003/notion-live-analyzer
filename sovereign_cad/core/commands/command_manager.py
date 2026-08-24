from __future__ import annotations

from .command import Command


class CommandManager:
    """
    Manages command execution and history.

    History model:

        execute
           |
           v
        undo stack
           |
        undo()
           |
           v
        redo stack
           |
        redo()
    """

    def __init__(self) -> None:

        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []

    # --------------------------------------------------------
    # Execute
    # --------------------------------------------------------

    def execute(self, command: Command) -> None:

        command.execute()

        self._undo_stack.append(command)

        # Any new operation invalidates redo history.
        self._redo_stack.clear()

    # --------------------------------------------------------
    # Undo
    # --------------------------------------------------------

    def undo(self) -> bool:

        if not self._undo_stack:
            return False

        command = self._undo_stack.pop()

        command.undo()

        self._redo_stack.append(command)

        return True

    # --------------------------------------------------------
    # Redo
    # --------------------------------------------------------

    def redo(self) -> bool:

        if not self._redo_stack:
            return False

        command = self._redo_stack.pop()

        command.execute()

        self._undo_stack.append(command)

        return True

    # --------------------------------------------------------
    # State
    # --------------------------------------------------------

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def undo_count(self) -> int:
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        return len(self._redo_stack)

    def clear(self) -> None:

        self._undo_stack.clear()
        self._redo_stack.clear()

    @property
    def undo_history(self) -> tuple[Command, ...]:
        return tuple(self._undo_stack)

    @property
    def redo_history(self) -> tuple[Command, ...]:
        return tuple(self._redo_stack)
