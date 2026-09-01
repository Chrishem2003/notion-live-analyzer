from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .retrieval import lexical_score
from .semantic import semantic_score


@dataclass
class RankedEvidence:

    content: str
    lexical: float
    semantic: float
    combined: float
    metadata: dict[str, Any]


class HybridRetriever:

    def __init__(
        self,
        lexical_weight: float = 0.45,
        semantic_weight: float = 0.55,
    ):

        total = (
            lexical_weight
            + semantic_weight
        )

        if total <= 0:
            raise ValueError(
                "Retrieval weights must be positive."
            )

        self.lexical_weight = (
            lexical_weight / total
        )

        self.semantic_weight = (
            semantic_weight / total
        )

    def rank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 10,
        metadata: list[dict[str, Any]]
        | None = None,
    ) -> list[RankedEvidence]:

        metadata = metadata or []

        ranked = []

        for index, document in enumerate(
            documents
        ):

            lexical = lexical_score(
                query,
                document,
            )

            semantic = semantic_score(
                query,
                document,
            )

            combined = (
                self.lexical_weight * lexical
                + self.semantic_weight * semantic
            )

            item_metadata = (
                metadata[index]
                if index < len(metadata)
                else {}
            )

            ranked.append(
                RankedEvidence(
                    content=document,
                    lexical=lexical,
                    semantic=semantic,
                    combined=combined,
                    metadata=item_metadata,
                )
            )

        ranked.sort(
            key=lambda item: item.combined,
            reverse=True,
        )

        return ranked[:top_k]
