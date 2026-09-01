from __future__ import annotations

import hashlib
import math
from typing import Sequence

from .embedding_provider import (
    EmbeddingProvider,
    EmbeddingResult,
)


class DeterministicEmbeddingProvider(
    EmbeddingProvider
):

    name = "deterministic"

    def __init__(
        self,
        dimensions: int = 384,
    ):

        if dimensions <= 0:
            raise ValueError(
                "Embedding dimensions must be positive."
            )

        self.dimensions = dimensions

    def _embed_one(
        self,
        text: str,
    ) -> list[float]:

        vector = [
            0.0
            for _ in range(
                self.dimensions
            )
        ]

        words = text.lower().split()

        if not words:
            return vector

        for word in words:

            digest = hashlib.sha256(
                word.encode("utf-8")
            ).digest()

            index = int.from_bytes(
                digest[:4],
                "big",
            ) % self.dimensions

            sign = (
                1.0
                if digest[4] % 2
                else -1.0
            )

            vector[index] += sign

        magnitude = math.sqrt(
            sum(
                value * value
                for value in vector
            )
        )

        if magnitude:

            vector = [
                value / magnitude
                for value in vector
            ]

        return vector

    def embed(
        self,
        texts: Sequence[str],
        model: str | None = None,
    ) -> EmbeddingResult:

        vectors = [
            self._embed_one(text)
            for text in texts
        ]

        return EmbeddingResult(
            vectors=vectors,
            model=model
            or "deterministic-384",
            provider=self.name,
            usage={
                "input_texts": len(texts)
            },
        )
