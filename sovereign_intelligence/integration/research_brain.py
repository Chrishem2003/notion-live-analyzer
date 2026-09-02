from __future__ import annotations

from typing import Any

from sovereign_intelligence.research import (
    ResearchEvidenceEngine,
    ResearchResult,
    plan_query,
)


class BrainResearchAdapter:
    """
    Thin Stage 46 integration layer.

    Existing KnowledgeEngine remains responsible for retrieval.

    Stage 46 adds evidence intelligence on top of those results:
        - normalization
        - provenance
        - reliability
        - freshness
        - diversity
        - deduplication
        - research ranking
    """

    def __init__(
        self,
        engine: ResearchEvidenceEngine | None = None,
    ):
        self.engine = engine or ResearchEvidenceEngine()

    def process(
        self,
        query: str,
        retrieval_result: Any,
        max_results: int = 5,
    ) -> ResearchResult:

        research_query = plan_query(
            query,
            max_results=max_results,
        )

        candidates = list(
            getattr(
                retrieval_result,
                "candidates",
                [],
            )
            or []
        )

        return self.engine.process(
            research_query,
            candidates,
        )

    @staticmethod
    def source_records(
        result: ResearchResult,
    ) -> list[dict[str, Any]]:

        records: list[dict[str, Any]] = []

        for evidence in result.evidence:

            provenance = evidence.provenance

            records.append(
                {
                    "id": evidence.id,
                    "score": evidence.research_score,
                    "relevance_score": evidence.relevance_score,
                    "reliability_score": evidence.reliability_score,
                    "freshness_score": evidence.freshness_score,
                    "diversity_score": evidence.diversity_score,
                    "provenance_score": evidence.provenance_score,
                    "source": evidence.source,
                    "source_type": evidence.source_type,
                    "metadata": dict(evidence.metadata),
                    "provenance": (
                        {
                            "source": provenance.source,
                            "source_type": provenance.source_type,
                            "retrieved_at": provenance.retrieved_at,
                            "identifier": provenance.identifier,
                            "location": provenance.location,
                            "metadata": dict(provenance.metadata),
                        }
                        if provenance is not None
                        else None
                    ),
                }
            )

        return records