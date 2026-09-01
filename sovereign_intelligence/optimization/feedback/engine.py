from __future__ import annotations

from .models import StrategyFeedback


class FeedbackEngine:

    @staticmethod
    def evaluate(
        strategy: str,
        problem_type: str,
        baseline_score: float,
        final_score: float,
        success: bool,
        metadata: dict | None = None,
    ) -> StrategyFeedback:

        if not 0 <= baseline_score <= 1:
            raise ValueError(
                "Baseline score must be between 0 and 1."
            )

        if not 0 <= final_score <= 1:
            raise ValueError(
                "Final score must be between 0 and 1."
            )

        improvement = (
            final_score
            - baseline_score
        )

        return StrategyFeedback(
            strategy=strategy,
            problem_type=problem_type,
            score=final_score,
            success=success,
            improvement=round(
                improvement,
                4,
            ),
            baseline_score=baseline_score,
            final_score=final_score,
            metadata=metadata or {},
        )
