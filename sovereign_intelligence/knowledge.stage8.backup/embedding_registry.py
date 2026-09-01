from __future__ import annotations

from .embedding_provider import (
    EmbeddingProvider,
)


class EmbeddingRegistry:

    def __init__(self):

        self._providers: dict[
            str,
            EmbeddingProvider,
        ] = {}

    def register(
        self,
        provider: EmbeddingProvider,
    ):

        self._providers[
            provider.name
        ] = provider

    def get(
        self,
        name: str,
    ) -> EmbeddingProvider:

        try:

            return self._providers[name]

        except KeyError:

            raise KeyError(
                f"Embedding provider not registered: {name}"
            )

    def names(self) -> list[str]:

        return sorted(
            self._providers.keys()
        )

    @classmethod
    def default(cls):

        from .embedding_deterministic import (
            DeterministicEmbeddingProvider,
        )

        registry = cls()

        registry.register(
            DeterministicEmbeddingProvider()
        )

        return registry
