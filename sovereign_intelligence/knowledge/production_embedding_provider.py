from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):

    name = "unknown"

    @property
    @abstractmethod
    def dimension(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        raise NotImplementedError

    def embed_one(
        self,
        text: str,
    ) -> list[float]:

        result = self.embed([text])

        if not result:
            raise RuntimeError(
                "Embedding provider returned no vector."
            )

        return result[0]
