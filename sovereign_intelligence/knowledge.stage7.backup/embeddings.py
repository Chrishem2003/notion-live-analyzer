from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence


class EmbeddingProvider(ABC):

    @abstractmethod
    def embed(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        raise NotImplementedError


class NullEmbeddingProvider(
    EmbeddingProvider
):

    def embed(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:

        return [
            []
            for _ in texts
        ]
