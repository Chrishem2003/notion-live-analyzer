from __future__ import annotations

from abc import ABC, abstractmethod
from ..models import Problem


class Agent(ABC):

    name = "general"

    @abstractmethod
    def instructions(self) -> str:
        raise NotImplementedError

    def can_handle(self, problem: Problem) -> bool:
        return True