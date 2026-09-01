from __future__ import annotations

from dataclasses import dataclass

from .embedding_provider_registry import (
    EmbeddingProviderRegistry,
)
from .production_embedding_provider import (
    EmbeddingProvider,
)


@dataclass
class EmbeddingBatchResult:

    vectors: list[list[float]]

    provider: str

    dimension: int


class ProductionEmbeddingService:

    def __init__(
        self,
        provider: EmbeddingProvider | None = None,
        registry: EmbeddingProviderRegistry
        | None = None,
        provider_name: str = "deterministic",
    ):

        self.registry = (
            registry
            or EmbeddingProviderRegistry.default()
        )

        self.provider = (
            provider
            or self.registry.get(provider_name)
        )

    @property
    def provider_name(self) -> str:

        return self.provider.name

    @property
    def dimension(self) -> int:

        return self.provider.dimension

    def embed(
        self,
        texts: list[str],
    ) -> EmbeddingBatchResult:

        if not isinstance(texts, list):
            raise TypeError(
                "texts must be a list."
            )

        cleaned = [
            str(text)
            for text in texts
        ]

        vectors = self.provider.embed(
            cleaned
        )

        if len(vectors) != len(cleaned):

            raise RuntimeError(
                "Embedding provider returned "
                "an incorrect number of vectors."
            )

        for vector in vectors:

            if len(vector) != self.dimension:

                raise RuntimeError(
                    "Embedding dimension mismatch."
                )

        return EmbeddingBatchResult(
            vectors=vectors,
            provider=self.provider_name,
            dimension=self.dimension,
        )

    def embed_one(
        self,
        text: str,
    ) -> list[float]:

        return self.embed(
            [text]
        ).vectors[0]
