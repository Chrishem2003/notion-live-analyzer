from __future__ import annotations

from abc import ABC, abstractmethod
from ..models import AIRequest, AIResponse


class ProviderError(RuntimeError):
    pass


class ModelProvider(ABC):

    name: str = "unknown"

    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        raise NotImplementedError