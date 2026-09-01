from __future__ import annotations

from .production_embedding_provider import (
    EmbeddingProvider,
)
from .embedding_deterministic_v2 import (
    DeterministicProvider,
)


class EmbeddingProviderRegistry:

    def __init__(self):

        self._providers: dict[
            str,
            EmbeddingProvider,
        ] = {}

    def register(
        self,
        provider: EmbeddingProvider,
    ) -> None:

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

            available = ", ".join(
                sorted(self._providers)
            )

            raise KeyError(
                f"Unknown embedding provider "
                f"'{name}'. Available: {available}"
            )

    def names(self) -> list[str]:

        return sorted(
            self._providers.keys()
        )

    @classmethod
    def default(cls):

        registry = cls()

        registry.register(
            DeterministicProvider()
        )

        return registry
