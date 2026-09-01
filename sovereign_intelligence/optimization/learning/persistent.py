from __future__ import annotations

from ..feedback.models import StrategyFeedback
from ..persistent import PersistentStrategyStore

from .learner import StrategyLearner
from .models import LearningDecision


class PersistentStrategyLearner:
    """
    Connects persistent strategy history and feedback
    to the Stage 37 learning engine.
    """

    def __init__(
        self,
        store: PersistentStrategyStore,
        minimum_samples: int = 3,
    ):
        self.store = store
        self.learner = StrategyLearner(
            minimum_samples=minimum_samples
        )
        self._load_history()

    def _load_history(self) -> None:
        with self.store._connect() as db:
            rows = db.execute(
                "SELECT DISTINCT problem_type "
                "FROM strategy_outcomes"
            ).fetchall()

        for row in rows:
            problem_type = str(row[0])

            records = self.store.recent(
                problem_type=problem_type,
                limit=10000,
            )

            for outcome in records:
                self.learner.record(
                    strategy=outcome.strategy,
                    problem_type=outcome.problem_type,
                    score=outcome.score,
                    success=outcome.success,
                    improvement=0.0,
                )

    def record_feedback(
        self,
        feedback: StrategyFeedback,
    ) -> None:
        self.learner.record(
            strategy=feedback.strategy,
            problem_type=feedback.problem_type,
            score=feedback.final_score,
            success=feedback.success,
            improvement=feedback.improvement,
        )

    def choose(
        self,
        problem_type: str = "general",
        default_strategy: str = "direct",
    ) -> LearningDecision:
        return self.learner.choose(
            problem_type=problem_type,
            default_strategy=default_strategy,
        )

    def rank(self, problem_type: str):
        return self.learner.rank(problem_type)

    def count(self) -> int:
        return self.learner.count()
