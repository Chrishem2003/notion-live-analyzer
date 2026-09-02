"""Research discovery-to-intake pipeline models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from sovereign_intelligence.research.discovery.models import (
    DiscoveryPlan,
    DiscoveryResult,
    SourceCandidate,
)
from sovereign_intelligence.research.intake.models import EvidenceRecord


@dataclass(frozen=True)
class PipelineResult:
    """Structured output from the discovery-to-intake pipeline."""

    query: str
    plan: DiscoveryPlan | None
    discovery: DiscoveryResult
    evidence: Sequence[EvidenceRecord] = field(default_factory=tuple)
    rejected: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def candidate_count(self) -> int:
        return len(self.discovery.candidates)

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)


@dataclass(frozen=True)
class PipelineSource:
    """Source candidate paired with material suitable for evidence intake."""

    candidate: SourceCandidate
    content: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
