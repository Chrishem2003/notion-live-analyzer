from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .learner import ContextAwareStrategyLearner
from .models import ProblemContext


@dataclass
class ComplexityStrategyDecision:
    strategy: str
    problem_type: str
    complexity: float
    complexity_band: str
    confidence: float
    reason: str
    ranked: list[Any]
    metadata: dict[str, Any]


class ComplexityAwareStrategyLearner:
    """
    Strategy learner that considers both problem type and complexity.

    Complexity bands:
        low    < 0.34
        medium < 0.67
        high   >= 0.67
    """

    def __init__(
        self,
        minimum_samples: int = 3,
    ):
        self.learner = ContextAwareStrategyLearner(
            minimum_samples=minimum_samples
        )

        self._complexity_records: list[dict[str, Any]] = []

    @staticmethod
    def complexity_band(complexity: float) -> str:
        if not 0.0 <= complexity <= 1.0:
            raise ValueError(
                "complexity must be between 0 and 1."
            )

        if complexity < 0.34:
            return "low"

        if complexity < 0.67:
            return "medium"

        return "high"

    def record(
        self,
        strategy: str,
        context: ProblemContext,
        score: float,
        success: bool,
        improvement: float = 0.0,
    ) -> None:

        if not strategy.strip():
            raise ValueError(
                "strategy cannot be empty."
            )

        if not 0.0 <= score <= 1.0:
            raise ValueError(
                "score must be between 0 and 1."
            )

        band = self.complexity_band(
            context.complexity
        )

        self._complexity_records.append(
            {
                "strategy": strategy,
                "problem_type": context.problem_type,
                "complexity": context.complexity,
                "complexity_band": band,
                "score": score,
                "success": bool(success),
                "improvement": improvement,
            }
        )

        self.learner.record(
            strategy=strategy,
            context=context,
            score=score,
            success=success,
            improvement=improvement,
        )

    def rank(
        self,
        context: ProblemContext,
    ):

        band = self.complexity_band(
            context.complexity
        )

        exact_records = [
            record
            for record in self._complexity_records
            if (
                record["problem_type"]
                == context.problem_type
                and record["complexity_band"]
                == band
            )
        ]

        if not exact_records:
            return self.learner.rank(
                context
            )

        grouped: dict[str, list[dict[str, Any]]] = {}

        for record in exact_records:
            grouped.setdefault(
                record["strategy"],
                [],
            ).append(record)

        ranked = []

        for strategy, records in grouped.items():
            samples = len(records)

            average_score = (
                sum(
                    item["score"]
                    for item in records
                )
                / samples
            )

            success_rate = (
                sum(
                    1
                    for item in records
                    if item["success"]
                )
                / samples
            )

            average_improvement = (
                sum(
                    item["improvement"]
                    for item in records
                )
                / samples
            )

            evidence = min(
                1.0,
                samples / self.learner.learner.minimum_samples,
            )

            improvement_signal = max(
                0.0,
                min(
                    1.0,
                    average_improvement + 0.5,
                ),
            )

            score = (
                average_score * 0.50
                + success_rate * 0.30
                + improvement_signal * 0.20
            )

            adjusted_score = (
                score * evidence
                + 0.5 * (1.0 - evidence)
            )

            ranked.append(
                {
                    "strategy": strategy,
                    "problem_type": context.problem_type,
                    "complexity_band": band,
                    "score": round(
                        adjusted_score,
                        4,
                    ),
                    "confidence": round(
                        evidence,
                        4,
                    ),
                    "samples": samples,
                    "success_rate": round(
                        success_rate,
                        4,
                    ),
                    "average_improvement": round(
                        average_improvement,
                        4,
                    ),
                }
            )

        ranked.sort(
            key=lambda item: (
                item["score"],
                item["confidence"],
                item["success_rate"],
            ),
            reverse=True,
        )

        return ranked

    def choose(
        self,
        context: ProblemContext,
        default_strategy: str = "direct",
    ) -> ComplexityStrategyDecision:

        band = self.complexity_band(
            context.complexity
        )

        ranked = self.rank(
            context
        )

        if not ranked:
            return ComplexityStrategyDecision(
                strategy=default_strategy,
                problem_type=context.problem_type,
                complexity=context.complexity,
                complexity_band=band,
                confidence=0.0,
                reason=(
                    "No historical evidence for this "
                    "problem context and complexity."
                ),
                ranked=[],
                metadata={
                    "complexity_aware": True,
                    "historical_evidence": False,
                },
            )

        winner = ranked[0]

        return ComplexityStrategyDecision(
            strategy=winner["strategy"],
            problem_type=context.problem_type,
            complexity=context.complexity,
            complexity_band=band,
            confidence=winner["confidence"],
            reason=(
                "Selected using historical strategy "
                "performance for the detected problem "
                "type and complexity band."
            ),
            ranked=ranked,
            metadata={
                "complexity_aware": True,
                "historical_evidence": True,
                "candidate_count": len(ranked),
            },
        )

    def count(self) -> int:
        return len(self._complexity_records)

    def clear(self) -> None:
        self._complexity_records.clear()
        self.learner.clear()
