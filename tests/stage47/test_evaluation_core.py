from __future__ import annotations

from dataclasses import dataclass, field

from sovereign_intelligence.research.evaluation.engine import (
    ResearchEvaluationEngine,
)
from sovereign_intelligence.research.models import ResearchResult
from sovereign_intelligence.research.query import ResearchQuery


@dataclass
class EvidenceFixture:
    """Minimal object matching the Stage 46 normalization contract."""

    content: str
    source: str
    id: str
    kind: str = ""
    score: float = 0.0
    metadata: dict = field(default_factory=dict)


def test_build_query_creates_stage46_query():
    engine = ResearchEvaluationEngine()

    query = engine.build_query(
        "research pipeline",
        intent="research",
        freshness_required=True,
        diversity_required=True,
        max_results=7,
    )

    assert isinstance(query, ResearchQuery)
    assert query.query == "research pipeline"
    assert query.intent == "research"
    assert query.freshness_required is True
    assert query.diversity_required is True
    assert query.max_results == 7


def test_evaluate_uses_stage46_engine():
    engine = ResearchEvaluationEngine()

    evidence = [
        EvidenceFixture(
            id="evidence-001",
            content="Research evidence about the pipeline.",
            source="local-document",
            kind="document",
            score=0.9,
        )
    ]

    result = engine.evaluate_query(
        "research pipeline",
        evidence,
    )

    assert isinstance(result.query, ResearchQuery)
    assert isinstance(result.result, ResearchResult)

    assert result.query.query == "research pipeline"
    assert result.total_candidates == 1
    assert result.evidence_count == 1

    assert result.metadata["engine"] == "ResearchEvidenceEngine"
    assert result.metadata["stage"] == 46


def test_evaluation_exposes_stage46_evidence():
    engine = ResearchEvaluationEngine()

    evidence = [
        EvidenceFixture(
            id="evidence-001",
            content="First research source.",
            source="source-a",
            kind="document",
            score=0.9,
        ),
        EvidenceFixture(
            id="evidence-002",
            content="Second research source.",
            source="source-b",
            kind="document",
            score=0.8,
        ),
    ]

    result = engine.evaluate_query(
        "research sources",
        evidence,
        max_results=10,
    )

    assert result.evidence_count == 2

    for item in result.evidence:
        assert item.id
        assert item.content
        assert item.source
        assert item.source_type
        assert isinstance(item.research_score, float)


def test_evaluation_metadata_matches_result():
    engine = ResearchEvaluationEngine()

    evidence = [
        EvidenceFixture(
            id="evidence-001",
            content="Evidence material.",
            source="local-document",
            kind="document",
            score=0.95,
        )
    ]

    result = engine.evaluate_query(
        "evidence material",
        evidence,
    )

    assert (
        result.metadata["evaluated_evidence"]
        == result.evidence_count
    )

    assert (
        result.metadata["total_candidates"]
        == result.total_candidates
    )

    assert (
        result.metadata["duplicates_removed"]
        == result.duplicates_removed
    )
