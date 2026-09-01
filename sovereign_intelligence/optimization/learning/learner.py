from __future__ import annotations

from collections import defaultdict

from .models import LearningDecision, StrategyScore


class StrategyLearner:
    def __init__(self, minimum_samples: int = 3):
        if minimum_samples < 1:
            raise ValueError("minimum_samples must be at least 1.")

        self.minimum_samples = minimum_samples
        self._records = []

    def record(
        self,
        strategy: str,
        problem_type: str,
        score: float,
        success: bool,
        improvement: float = 0.0,
    ) -> None:
        if not strategy.strip():
            raise ValueError("Strategy cannot be empty.")

        if not problem_type.strip():
            raise ValueError("Problem type cannot be empty.")

        if not 0 <= score <= 1:
            raise ValueError("Score must be between 0 and 1.")

        self._records.append(
            {
                "strategy": strategy,
                "problem_type": problem_type,
                "score": score,
                "success": bool(success),
                "improvement": improvement,
            }
        )

    def rank(self, problem_type: str) -> list[StrategyScore]:
        if not problem_type.strip():
            raise ValueError("Problem type cannot be empty.")

        grouped = defaultdict(list)

        for record in self._records:
            if record["problem_type"] == problem_type:
                grouped[record["strategy"]].append(record)

        results = []

        for strategy, records in grouped.items():
            samples = len(records)

            average_score = sum(
                item["score"] for item in records
            ) / samples

            success_rate = sum(
                1 for item in records if item["success"]
            ) / samples

            average_improvement = sum(
                item["improvement"] for item in records
            ) / samples

            evidence = min(
                1.0,
                samples / self.minimum_samples,
            )

            improvement_signal = max(
                0.0,
                min(1.0, average_improvement + 0.5),
            )

            base_score = (
                average_score * 0.50
                + success_rate * 0.30
                + improvement_signal * 0.20
            )

            adjusted_score = (
                base_score * evidence
                + 0.5 * (1.0 - evidence)
            )

            results.append(
                StrategyScore(
                    strategy=strategy,
                    problem_type=problem_type,
                    score=round(adjusted_score, 4),
                    confidence=round(evidence, 4),
                    samples=samples,
                    success_rate=round(success_rate, 4),
                    average_improvement=round(
                        average_improvement,
                        4,
                    ),
                )
            )

        results.sort(
            key=lambda item: (
                item.score,
                item.confidence,
                item.success_rate,
                item.average_improvement,
            ),
            reverse=True,
        )

        return results

    def choose(
        self,
        problem_type: str,
        default_strategy: str = "direct",
    ) -> LearningDecision:
        ranked = self.rank(problem_type)

        if not ranked:
            return LearningDecision(
                strategy=default_strategy,
                problem_type=problem_type,
                confidence=0.0,
                reason="No historical evidence; using default strategy.",
            )

        winner = ranked[0]

        return LearningDecision(
            strategy=winner.strategy,
            problem_type=problem_type,
            confidence=winner.confidence,
            reason="Selected from learned historical strategy performance.",
            ranked=ranked,
        )

    def count(self) -> int:
        return len(self._records)

    def clear(self) -> None:
        self._records.clear()
