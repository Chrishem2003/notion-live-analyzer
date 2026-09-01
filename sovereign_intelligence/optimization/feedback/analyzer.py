from __future__ import annotations

from collections import defaultdict

from .models import (
    FeedbackSummary,
    StrategyFeedback,
)


class FeedbackAnalyzer:

    def __init__(self):

        self._feedback: list[
            StrategyFeedback
        ] = []

    def record(
        self,
        feedback: StrategyFeedback,
    ) -> None:

        if not feedback.strategy.strip():
            raise ValueError(
                "Strategy cannot be empty."
            )

        if not feedback.problem_type.strip():
            raise ValueError(
                "Problem type cannot be empty."
            )

        if not 0 <= feedback.score <= 1:
            raise ValueError(
                "Score must be between 0 and 1."
            )

        self._feedback.append(
            feedback
        )

    def summaries(
        self,
        problem_type: str | None = None,
    ) -> list[FeedbackSummary]:

        grouped = defaultdict(list)

        for feedback in self._feedback:

            if (
                problem_type is not None
                and feedback.problem_type
                != problem_type
            ):
                continue

            grouped[
                (
                    feedback.strategy,
                    feedback.problem_type,
                )
            ].append(feedback)

        results = []

        for (
            strategy,
            ptype,
        ), records in grouped.items():

            samples = len(records)

            successes = sum(
                1
                for record in records
                if record.success
            )

            average_score = (
                sum(
                    record.score
                    for record in records
                )
                / samples
            )

            average_improvement = (
                sum(
                    record.improvement
                    for record in records
                )
                / samples
            )

            success_rate = (
                successes / samples
            )

            results.append(
                FeedbackSummary(
                    strategy=strategy,
                    problem_type=ptype,
                    samples=samples,
                    successes=successes,
                    average_score=round(
                        average_score,
                        4,
                    ),
                    average_improvement=round(
                        average_improvement,
                        4,
                    ),
                    success_rate=round(
                        success_rate,
                        4,
                    ),
                )
            )

        results.sort(
            key=lambda item: (
                item.average_improvement,
                item.average_score,
                item.success_rate,
            ),
            reverse=True,
        )

        return results

    def best(
        self,
        problem_type: str,
    ) -> FeedbackSummary | None:

        summaries = self.summaries(
            problem_type
        )

        if not summaries:
            return None

        return summaries[0]

    def count(self) -> int:

        return len(self._feedback)

    def clear(self) -> None:

        self._feedback.clear()
