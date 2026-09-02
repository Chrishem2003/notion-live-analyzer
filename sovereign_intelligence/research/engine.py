from __future__ import annotations

import hashlib
from typing import Any, Iterable

from .deduplicator import deduplicate
from .evaluator import evaluate
from .models import (
    ResearchEvidence,
    ResearchQuery,
    ResearchResult,
)
from .provenance import (
    build_provenance,
    infer_source_type,
    provenance_score,
)
from .ranker import rank


class ResearchEvidenceEngine:

    def normalize(
        self,
        evidence: Iterable[Any],
    ) -> list[ResearchEvidence]:

        normalized: list[ResearchEvidence] = []

        for index, item in enumerate(evidence):

            content = str(
                getattr(item, "content", "")
                or ""
            ).strip()

            if not content:
                continue

            source = str(
                getattr(item, "source", "")
                or getattr(item, "id", "")
                or f"evidence-{index}"
            )

            metadata = dict(
                getattr(item, "metadata", {})
                or {}
            )

            kind = str(
                getattr(item, "kind", "")
                or metadata.get(
                    "kind",
                    "",
                )
            )

            source_type = infer_source_type(
                source,
                kind,
            )

            relevance = getattr(
                item,
                "score",
                None,
            )

            if relevance is None:
                relevance = getattr(
                    item,
                    "fused_score",
                    0.0,
                )

            try:
                relevance = float(
                    relevance or 0.0
                )
            except (TypeError, ValueError):
                relevance = 0.0

            evidence_id = hashlib.sha256(
                (
                    source
                    + "\n"
                    + content
                ).encode(
                    "utf-8",
                    errors="replace",
                )
            ).hexdigest()[:24]

            record = ResearchEvidence(
                id=evidence_id,
                content=content,
                source=source,
                source_type=source_type,
                relevance_score=max(
                    0.0,
                    min(1.0, relevance),
                ),
                metadata=metadata,
            )

            record.provenance = build_provenance(
                source,
                source_type,
                metadata,
            )

            record.provenance_score = provenance_score(
                record
            )

            normalized.append(
                evaluate(record)
            )

        return normalized

    def process(
        self,
        query: ResearchQuery,
        evidence: Iterable[Any],
    ) -> ResearchResult:

        normalized = self.normalize(evidence)

        total_candidates = len(normalized)

        unique, duplicates_removed = (
            deduplicate(normalized)
        )

        ranked = rank(unique)

        ranked = ranked[
            :query.max_results
        ]

        if query.freshness_required:
            ranked.sort(
                key=lambda item: (
                    item.freshness_score,
                    item.research_score,
                ),
                reverse=True,
            )

        if query.diversity_required:
            ranked.sort(
                key=lambda item: (
                    item.diversity_score,
                    item.research_score,
                ),
                reverse=True,
            )

        return ResearchResult(
            query=query,
            evidence=ranked,
            total_candidates=total_candidates,
            duplicates_removed=duplicates_removed,
            metadata={
                "engine": "stage46",
                "normalization": "native",
            },
        )
