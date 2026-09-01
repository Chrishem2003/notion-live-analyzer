from __future__ import annotations

from ..feedback.models import StrategyFeedback
from ..learning.persistent import PersistentStrategyLearner
from ..models import StrategyOutcome
from ..persistent import PersistentStrategyStore


class PersistentFeedbackLearner:
    """Persist optimization feedback and update the strategy learner."""

    def __init__(
        self,
        store: PersistentStrategyStore,
        learner: PersistentStrategyLearner | None = None,
    ):
        self.store = store
        self.learner = learner or PersistentStrategyLearner(store)

    def record(self, feedback: StrategyFeedback) -> None:
        if not feedback.strategy.strip():
            raise ValueError("Feedback strategy cannot be empty.")

        if not feedback.problem_type.strip():
            raise ValueError("Feedback problem type cannot be empty.")

        outcome = StrategyOutcome(
            strategy=feedback.strategy,
            problem_type=feedback.problem_type,
            score=feedback.final_score,
            success=feedback.success,
            metadata=feedback.metadata,
        )

        self.store.record(outcome)
        self.learner.record_feedback(feedback)

    def choose(
        self,
        problem_type: str = "general",
        default_strategy: str = "direct",
    ):
        return self.learner.choose(
            problem_type=problem_type,
            default_strategy=default_strategy,
        )

    def history_count(self, problem_type: str = "general") -> int:
        return self.store.count(problem_type)
