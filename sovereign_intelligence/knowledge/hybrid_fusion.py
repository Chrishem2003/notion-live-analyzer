from __future__ import annotations

from dataclasses import replace

from .retrieval_models import (
    RetrievalCandidate,
    RetrievalResult,
)


class HybridFusion:

    def __init__(
        self,
        lexical_weight: float = 0.35,
        semantic_weight: float = 0.65,
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

    def combine(
        self,
        query: str,
        lexical: list[
            RetrievalCandidate
        ],
        semantic: list[
            RetrievalCandidate
        ],
        top_k: int = 10,
    ) -> RetrievalResult:

        combined = {}

        for item in lexical:

            combined[item.id] = replace(
                item
            )

        for item in semantic:

            if item.id not in combined:

                combined[item.id] = replace(
                    item
                )

            else:

                combined[
                    item.id
                ].semantic_score = (
                    item.semantic_score
                )

                if item.metadata:

                    combined[
                        item.id
                    ].metadata.update(
                        item.metadata
                    )

        ranked = []

        for item in combined.values():

            fused = (
                self.lexical_weight
                * item.lexical_score
                +
                self.semantic_weight
                * item.semantic_score
            )

            item.fused_score = fused

            ranked.append(item)

        ranked.sort(
            key=lambda item: item.fused_score,
            reverse=True,
        )

        return RetrievalResult(
            query=query,
            candidates=ranked[:top_k],
            strategy="hybrid",
            metadata={
                "lexical_weight":
                    self.lexical_weight,
                "semantic_weight":
                    self.semantic_weight,
            },
        )
