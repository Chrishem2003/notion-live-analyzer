from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class SourceCandidate:
    """
    A discovered source candidate.

    This is metadata about a source, not fabricated source content.
    """

    source_id: str
    source: str
    source_type: str
    title: str = ""
    location: str = ""
    description: str = ""
    discovered_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        source_id: str,
        source: str,
        source_type: str,
        title: str = "",
        location: str = "",
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> "SourceCandidate":

        return cls(
            source_id=source_id,
            source=source,
            source_type=source_type,
            title=title,
            location=location,
            description=description,
            discovered_at=datetime.now(
                timezone.utc
            ).isoformat(),
            metadata=dict(metadata or {}),
        )


@dataclass(frozen=True)
class ResearchObjective:
    """
    A single research objective generated from a user request.
    """

    objective_id: str
    description: str
    priority: float = 1.0
    queries: tuple[str, ...] = ()


@dataclass
class DiscoveryPlan:
    """
    Structured research-discovery plan.

    The plan describes what should be discovered without claiming
    that discovery has already occurred.
    """

    query: str
    intent: str
    objectives: list[ResearchObjective] = field(
        default_factory=list
    )
    source_types: list[str] = field(
        default_factory=list
    )
    search_queries: list[str] = field(
        default_factory=list
    )
    freshness_required: bool = False
    diversity_required: bool = False
    max_sources: int = 10
    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class DiscoveryResult:
    """
    Result returned by the discovery engine.

    Candidates are source descriptions. Actual evidence retrieval
    remains a separate concern.
    """

    query: str
    candidates: list[SourceCandidate] = field(
        default_factory=list
    )
    total_candidates: int = 0
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def sources(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for candidate in self.candidates:
            if candidate.source not in seen:
                seen.add(candidate.source)
                result.append(candidate.source)

        return result
