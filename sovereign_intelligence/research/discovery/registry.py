from __future__ import annotations

from .models import DiscoveryPlan, SourceCandidate
from .sources import SourceDiscoveryAdapter


class SourceRegistry:
    """
    Registry of source-discovery adapters.

    Adapters are explicitly registered. No provider is assumed to
    exist unless it has been registered.
    """

    def __init__(self):
        self._adapters: dict[str, SourceDiscoveryAdapter] = {}

    def register(
        self,
        name: str,
        adapter: SourceDiscoveryAdapter,
    ) -> None:

        normalized = str(name).strip().lower()

        if not normalized:
            raise ValueError(
                "Adapter name cannot be empty."
            )

        self._adapters[normalized] = adapter

    def unregister(self, name: str) -> None:
        self._adapters.pop(
            str(name).strip().lower(),
            None,
        )

    def get(
        self,
        name: str,
    ) -> SourceDiscoveryAdapter | None:

        return self._adapters.get(
            str(name).strip().lower()
        )

    def names(self) -> list[str]:
        return sorted(self._adapters)

    def discover(
        self,
        plan: DiscoveryPlan,
    ) -> list[SourceCandidate]:

        candidates: list[SourceCandidate] = []

        for name in self.names():

            adapter = self._adapters[name]

            discovered = adapter.discover(plan)

            candidates.extend(discovered)

        return candidates
