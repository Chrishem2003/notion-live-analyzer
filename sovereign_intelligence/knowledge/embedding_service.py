from __future__ import annotations

from typing import Sequence

from .embedding_provider import (
    EmbeddingResult,
)
from .embedding_registry import (
    EmbeddingRegistry,
)


class EmbeddingService:

    def __init__(
        self,
        registry: EmbeddingRegistry | None = None,
        provider: str = "deterministic",
    ):

        self.registry = (
            registry
            or EmbeddingRegistry.default()
        )

        self.provider_name = provider

    @property
    def provider(self):

        return self.registry.get(
            self.provider_name
        )

    def embed(
        self,
        texts: Sequence[str],
        model: str | None = None,
    ) -> EmbeddingResult:

        return self.provider.embed(
            texts,
            model=model,
        )

    def embed_one(
        self,
        text: str,
        model: str | None = None,
    ) -> list[float]:

        result = self.embed(
            [text],
            model=model,
        )

        return result.vectors[0]
