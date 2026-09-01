from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):

    name = "tool"
    description = ""

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        raise NotImplementedError