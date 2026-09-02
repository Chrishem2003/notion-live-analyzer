from __future__ import annotations

from .models import DiscoveryPlan, DiscoveryResult, SourceCandidate
from .registry import SourceRegistry


class SourceDiscoveryEngine:
    """
    Coordinates registered source-discovery adapters.

    Discovery is intentionally separate from evidence retrieval.
    """

    def __init__(
        self,
        registry: SourceRegistry | None = None,
    ):
        self.registry = registry or SourceRegistry()

    @staticmethod
    def _deduplicate(
        candidates: list[SourceCandidate],
    ) -> list[SourceCandidate]:

        seen: set[tuple[str, str, str]] = set()
        result: list[SourceCandidate] = []

        for candidate in candidates:

            key = (
                candidate.source_id,
                candidate.source,
                candidate.location,
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(candidate)

        return result

    def discover(
        self,
        plan: DiscoveryPlan,
    ) -> DiscoveryResult:

        discovered = self.registry.discover(plan)

        unique = self._deduplicate(discovered)

        limited = unique[: max(
            1,
            plan.max_sources,
        )]

        return DiscoveryResult(
            query=plan.query,
            candidates=limited,
            total_candidates=len(unique),
            metadata={
                "intent": plan.intent,
                "registered_adapters": (
                    self.registry.names()
                ),
                "freshness_required": (
                    plan.freshness_required
                ),
                "diversity_required": (
                    plan.diversity_required
                ),
            },
        )

    def discover_query(
        self,
        query: str,
        plan_factory=None,
        max_sources: int = 10,
    ) -> DiscoveryResult:

        if plan_factory is None:
            from .planner import plan_discovery

            plan_factory = plan_discovery

        plan = plan_factory(
            query,
            max_sources=max_sources,
        )

        return self.discover(plan)
