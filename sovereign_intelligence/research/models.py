from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class EvidenceProvenance:
    source: str
    source_type: str
    retrieved_at: str
    identifier: str = ""
    location: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        source: str,
        source_type: str,
        identifier: str = "",
        location: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> "EvidenceProvenance":
        return cls(
            source=source,
            source_type=source_type,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            identifier=identifier,
            location=location,
            metadata=dict(metadata or {}),
        )


@dataclass
class ResearchEvidence:
    id: str
    content: str
    source: str
    source_type: str

    relevance_score: float = 0.0
    reliability_score: float = 0.0
    freshness_score: float = 0.0
    diversity_score: float = 0.0
    provenance_score: float = 0.0
    research_score: float = 0.0

    provenance: EvidenceProvenance | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def score_tuple(self) -> tuple[float, ...]:
        return (
            self.research_score,
            self.relevance_score,
            self.reliability_score,
            self.freshness_score,
            self.diversity_score,
            self.provenance_score,
        )


@dataclass
class ResearchQuery:
    query: str
    intent: str = "general"
    freshness_required: bool = False
    diversity_required: bool = False
    max_results: int = 10
    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class ResearchResult:
    query: ResearchQuery
    evidence: list[ResearchEvidence]

    total_candidates: int = 0
    duplicates_removed: int = 0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def sources(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for item in self.evidence:
            if item.source in seen:
                continue

            seen.add(item.source)
            result.append(item.source)

        return result
