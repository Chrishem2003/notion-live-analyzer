from __future__ import annotations

import hashlib
import math

from .production_embedding_provider import (
    EmbeddingProvider,
)


class DeterministicProvider(
    EmbeddingProvider
):

    name = "deterministic"

    def __init__(
        self,
        dimension: int = 384,
    ):

        if dimension <= 0:
            raise ValueError(
                "Embedding dimension must be positive."
            )

        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _embed_text(
        self,
        text: str,
    ) -> list[float]:

        vector = [0.0] * self._dimension

        words = text.lower().split()

        for word in words:

            digest = hashlib.sha256(
                word.encode("utf-8")
            ).digest()

            index = int.from_bytes(
                digest[:4],
                "big",
            ) % self._dimension

            sign = (
                1.0
                if digest[4] % 2
                else -1.0
            )

            vector[index] += sign

        magnitude = math.sqrt(
            sum(value * value for value in vector)
        )

        if magnitude:

            vector = [
                value / magnitude
                for value in vector
            ]

        return vector

    def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        return [
            self._embed_text(text)
            for text in texts
        ]
