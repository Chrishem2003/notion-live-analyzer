"""Stage 47 research evidence evaluation engine."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sovereign_intelligence.research.engine import ResearchEvidenceEngine
from sovereign_intelligence.research.query import ResearchQuery
from sovereign_intelligence.research.models import ResearchResult

from .models import EvaluationResult


class ResearchEvaluationEngine:
    """
    Evaluate research evidence using the Stage 46 evidence intelligence engine.

    This layer intentionally does not duplicate normalization, provenance,
    reliability, freshness, diversity, deduplication, or ranking logic.
    Stage 46 remains the authoritative implementation for those operations.
    """

    def __init__(
        self,
        evidence_engine: ResearchEvidenceEngine | None = None,
    ) -> None:
        self.evidence_engine = (
            evidence_engine or ResearchEvidenceEngine()
        )

    @staticmethod
    def build_query(
        query: str,
        *,
        intent: str = "general",
        freshness_required: bool = False,
        diversity_required: bool = False,
        max_results: int = 10,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchQuery:
        """Build a Stage 46-compatible research query."""
        return ResearchQuery(
            query=query,
            intent=intent,
            freshness_required=freshness_required,
            diversity_required=diversity_required,
            max_results=max_results,
            metadata=dict(metadata or {}),
        )

    def evaluate(
        self,
        query: ResearchQuery,
        evidence: Iterable[Any],
    ) -> EvaluationResult:
        """Evaluate evidence through the existing Stage 46 engine."""
        result = self.evidence_engine.process(
            query,
            evidence,
        )

        if not isinstance(result, ResearchResult):
            raise TypeError(
                "ResearchEvidenceEngine.process() must return "
                "ResearchResult"
            )

        return EvaluationResult(
            query=query,
            result=result,
            metadata={
                "engine": "ResearchEvidenceEngine",
                "stage": 46,
                "evaluated_evidence": len(result.evidence),
                "total_candidates": result.total_candidates,
                "duplicates_removed": result.duplicates_removed,
            },
        )

    def evaluate_query(
        self,
        query: str,
        evidence: Iterable[Any],
        *,
        intent: str = "general",
        freshness_required: bool = False,
        diversity_required: bool = False,
        max_results: int = 10,
        metadata: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """Build a research query and evaluate supplied evidence."""
        research_query = self.build_query(
            query,
            intent=intent,
            freshness_required=freshness_required,
            diversity_required=diversity_required,
            max_results=max_results,
            metadata=metadata,
        )

        return self.evaluate(
            research_query,
            evidence,
        )
