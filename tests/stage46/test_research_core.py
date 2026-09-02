from __future__ import annotations

from sovereign_intelligence.knowledge.evidence import (
    EvidenceItem,
)

from sovereign_intelligence.knowledge.retrieval_models import (
    RetrievalCandidate,
)

from sovereign_intelligence.research import (
    ResearchEvidenceEngine,
    detect_intent,
    plan_query,
)


def test_imports() -> None:
    assert EvidenceItem is not None
    assert RetrievalCandidate is not None
    assert ResearchEvidenceEngine is not None


def test_intent_detection() -> None:
    assert detect_intent(
        "What is the latest version?"
    ) == "freshness"

    assert detect_intent(
        "Compare these two approaches"
    ) == "comparative"

    assert detect_intent(
        "Provide evidence and sources"
    ) == "evidence"


def test_evidence_item_normalization() -> None:

    source = EvidenceItem(
        source="document-a",
        content="Important evidence content.",
        score=0.91,
        kind="document",
        metadata={
            "verified": True,
        },
    )

    engine = ResearchEvidenceEngine()

    result = engine.process(
        plan_query(
            "Provide evidence",
            max_results=5,
        ),
        [source],
    )

    assert result.total_candidates == 1
    assert len(result.evidence) == 1

    item = result.evidence[0]

    assert item.source == "document-a"
    assert item.content == (
        "Important evidence content."
    )
    assert item.relevance_score == 0.91
    assert item.reliability_score > 0.8
    assert item.provenance_score > 0.0
    assert item.research_score > 0.0


def test_retrieval_candidate_normalization() -> None:

    candidate = RetrievalCandidate(
        id="candidate-1",
        content="Hybrid retrieval evidence.",
        lexical_score=0.70,
        semantic_score=0.80,
        fused_score=0.90,
        metadata={
            "verified": True,
        },
    )

    engine = ResearchEvidenceEngine()

    result = engine.process(
        plan_query(
            "research this",
            max_results=5,
        ),
        [candidate],
    )

    assert len(result.evidence) == 1
    assert result.evidence[0].relevance_score == 0.90


def test_duplicate_removal() -> None:

    first = EvidenceItem(
        source="a",
        content="Same evidence.",
        score=0.8,
    )

    second = EvidenceItem(
        source="b",
        content="Same evidence.",
        score=0.7,
    )

    engine = ResearchEvidenceEngine()

    result = engine.process(
        plan_query(
            "research",
            max_results=10,
        ),
        [first, second],
    )

    assert result.total_candidates == 2
    assert result.duplicates_removed == 1
    assert len(result.evidence) == 1


def test_multiple_sources() -> None:

    evidence = [
        EvidenceItem(
            source="source-a",
            content="Evidence A",
            score=0.9,
        ),
        EvidenceItem(
            source="source-b",
            content="Evidence B",
            score=0.8,
        ),
    ]

    engine = ResearchEvidenceEngine()

    result = engine.process(
        plan_query(
            "compare the evidence",
            max_results=10,
        ),
        evidence,
    )

    assert len(result.evidence) == 2
    assert len(result.sources) == 2


if __name__ == "__main__":
    test_imports()
    test_intent_detection()
    test_evidence_item_normalization()
    test_retrieval_candidate_normalization()
    test_duplicate_removal()
    test_multiple_sources()
    print("STAGE46_ISOLATED_TESTS_OK")
