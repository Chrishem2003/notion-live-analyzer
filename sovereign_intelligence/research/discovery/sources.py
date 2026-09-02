from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import DiscoveryPlan, SourceCandidate


class SourceDiscoveryAdapter(ABC):
    """
    Contract for real source-discovery providers.

    Implementations must return source metadata only.
    They must not fabricate evidence content.
    """

    source_type: str = "unknown"

    @abstractmethod
    def discover(
        self,
        plan: DiscoveryPlan,
    ) -> list[SourceCandidate]:
        raise NotImplementedError


class StaticSourceAdapter(SourceDiscoveryAdapter):
    """
    Deterministic adapter useful for local integration and tests.

    It returns explicitly supplied source candidates.
    """

    source_type = "static"

    def __init__(
        self,
        candidates: list[SourceCandidate] | None = None,
    ):
        self._candidates = list(candidates or [])

    def discover(
        self,
        plan: DiscoveryPlan,
    ) -> list[SourceCandidate]:

        allowed = set(plan.source_types)

        return [
            candidate
            for candidate in self._candidates
            if not allowed
            or candidate.source_type in allowed
        ]


class ExistingSourceAdapter(SourceDiscoveryAdapter):
    """
    Adapter for an existing source collection.

    This deliberately accepts already-known source metadata rather
    than pretending to perform an external search.
    """

    source_type = "existing"

    def __init__(
        self,
        sources: list[dict[str, Any]] | None = None,
    ):
        self._sources = list(sources or [])

    def discover(
        self,
        plan: DiscoveryPlan,
    ) -> list[SourceCandidate]:

        result: list[SourceCandidate] = []

        for index, item in enumerate(self._sources):

            source = str(
                item.get(
                    "source",
                    item.get("id", "unknown"),
                )
            )

            source_type = str(
                item.get(
                    "source_type",
                    item.get("kind", "unknown"),
                )
            )

            if (
                plan.source_types
                and source_type not in plan.source_types
            ):
                continue

            result.append(
                SourceCandidate.create(
                    source_id=str(
                        item.get(
                            "id",
                            f"existing-{index}",
                        )
                    ),
                    source=source,
                    source_type=source_type,
                    title=str(
                        item.get("title", "")
                    ),
                    location=str(
                        item.get("location", "")
                    ),
                    description=str(
                        item.get("description", "")
                    ),
                    metadata=dict(
                        item.get(
                            "metadata",
                            {},
                        )
                        or {}
                    ),
                )
            )

        return result
