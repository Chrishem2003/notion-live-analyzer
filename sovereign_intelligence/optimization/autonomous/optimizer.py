from __future__ import annotations

from .models import OptimizationCandidate, OptimizationResult


class AutonomousOptimizer:
    """
    Selects and evaluates strategy candidates using learned performance.

    The optimizer is deliberately conservative:
    - It requires candidates to have evidence.
    - It preserves the current strategy when there is no clear improvement.
    - It does not execute tools or providers itself.
    """

    def __init__(self, minimum_improvement: float = 0.02):
        if minimum_improvement < 0:
            raise ValueError(
                "minimum_improvement must be non-negative."
            )

        self.minimum_improvement = minimum_improvement

    def candidates(self, ranked, problem_type: str):
        results = []

        for index, item in enumerate(ranked, start=1):
            results.append(
                OptimizationCandidate(
                    strategy=item.strategy,
                    problem_type=problem_type,
                    expected_score=item.score,
                    confidence=item.confidence,
                    rank=index,
                    reason=(
                        "Ranked from learned strategy performance."
                    ),
                )
            )

        return results

    def optimize(
        self,
        current_strategy: str,
        current_score: float,
        ranked,
        problem_type: str,
    ) -> OptimizationResult:

        if not current_strategy.strip():
            raise ValueError(
                "current_strategy cannot be empty."
            )

        if not 0 <= current_score <= 1:
            raise ValueError(
                "current_score must be between 0 and 1."
            )

        candidates = self.candidates(
            ranked,
            problem_type,
        )

        if not candidates:
            return OptimizationResult(
                strategy=current_strategy,
                problem_type=problem_type,
                previous_score=current_score,
                new_score=current_score,
                improvement=0.0,
                optimized=False,
                confidence=0.0,
                candidates=[],
                metadata={
                    "reason": "No learned candidates available."
                },
            )

        best = candidates[0]

        improvement = best.expected_score - current_score

        should_optimize = (
            best.strategy != current_strategy
            and improvement >= self.minimum_improvement
        )

        if should_optimize:
            selected_strategy = best.strategy
            new_score = best.expected_score
        else:
            selected_strategy = current_strategy
            new_score = current_score

        return OptimizationResult(
            strategy=selected_strategy,
            problem_type=problem_type,
            previous_score=current_score,
            new_score=round(new_score, 4),
            improvement=round(
                new_score - current_score,
                4,
            ),
            optimized=should_optimize,
            confidence=best.confidence,
            candidates=candidates,
            metadata={
                "candidate_strategy": best.strategy,
                "candidate_score": best.expected_score,
                "minimum_improvement": self.minimum_improvement,
            },
        )
