from __future__ import annotations

from .retrieval_models import (
    RetrievalCandidate,
)


def token_set(text: str) -> set[str]:

    return set(
        text.lower().split()
    )


def overlap(
    left: str,
    right: str,
) -> float:

    a = token_set(left)

    b = token_set(right)

    if not a or not b:
        return 0.0

    return len(a & b) / min(
        len(a),
        len(b),
    )


class DiversityReranker:

    def __init__(
        self,
        diversity_penalty: float = 0.20,
    ):

        self.diversity_penalty = (
            max(
                0.0,
                min(
                    1.0,
                    diversity_penalty,
                ),
            )
        )

    def rerank(
        self,
        candidates: list[
            RetrievalCandidate
        ],
        top_k: int = 10,
    ) -> list[RetrievalCandidate]:

        remaining = list(candidates)

        selected = []

        while remaining and len(
            selected
        ) < top_k:

            best = None

            best_score = float(
                "-inf"
            )

            for candidate in remaining:

                penalty = 0.0

                for chosen in selected:

                    penalty = max(
                        penalty,
                        overlap(
                            candidate.content,
                            chosen.content,
                        ),
                    )

                score = (
                    candidate.fused_score
                    -
                    self.diversity_penalty
                    * penalty
                )

                if score > best_score:

                    best_score = score

                    best = candidate

            if best is None:
                break

            selected.append(best)

            remaining.remove(best)

        return selected
