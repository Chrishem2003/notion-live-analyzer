from __future__ import annotations

from .models import ResearchEvidence


def rank(
    evidence: list[ResearchEvidence],
) -> list[ResearchEvidence]:

    if not evidence:
        return []

    source_counts: dict[str, int] = {}

    for item in evidence:
        source_counts[item.source] = (
            source_counts.get(item.source, 0) + 1
        )

    for item in evidence:

        source_count = source_counts.get(
            item.source,
            1,
        )

        item.diversity_score = (
            1.0 / source_count
        )

        item.research_score = (
            (item.relevance_score * 0.40)
            + (item.reliability_score * 0.20)
            + (item.freshness_score * 0.15)
            + (item.diversity_score * 0.10)
            + (item.provenance_score * 0.10)
            + (
                float(
                    item.metadata.get(
                        "completeness_score",
                        0.0,
                    )
                )
                * 0.05
            )
        )

    return sorted(
        evidence,
        key=lambda item: item.score_tuple(),
        reverse=True,
    )
