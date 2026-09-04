"""Stage 47 research evaluation models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from sovereign_intelligence.research.models import ResearchResult
from sovereign_intelligence.research.query import ResearchQuery


@dataclass(frozen=True)
class EvaluationResult:
    """Structured result produced by the Stage 47 evaluation layer."""

    query: ResearchQuery
    result: ResearchResult
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def evidence(self):
        """Return evaluated research evidence."""
        return self.result.evidence

    @property
    def evidence_count(self) -> int:
        """Return the number of evaluated evidence records."""
        return len(self.result.evidence)

    @property
    def total_candidates(self) -> int:
        """Return the number of candidates evaluated."""
        return self.result.total_candidates

    @property
    def duplicates_removed(self) -> int:
        """Return the number of duplicate records removed."""
        return self.result.duplicates_removed
