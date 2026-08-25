from __future__ import annotations

from abc import ABC, abstractmethod


class Command(ABC):
    """
    Base class for every document-changing operation.

    A command must be reversible.

    execute()
        Apply the operation.

    undo()
        Reverse the operation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def execute(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def undo(self) -> None:
        raise NotImplementedError
