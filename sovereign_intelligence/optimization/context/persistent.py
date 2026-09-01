from __future__ import annotations

from ..persistent import PersistentStrategyStore
from .learner import ContextAwareStrategyLearner
from .models import ProblemContext


class PersistentContextAwareLearner:
    """Persistent context-aware strategy learning."""

    def __init__(
        self,
        store: PersistentStrategyStore,
        minimum_samples: int = 3,
    ):
        self.store = store
        self.learner = ContextAwareStrategyLearner(
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

            outcomes = self.store.recent(
                problem_type=problem_type,
                limit=10000,
            )

            context = ProblemContext(
                problem_type=problem_type,
                complexity=0.0,
                requires_reasoning=problem_type == "reasoning",
                requires_code=problem_type == "coding",
                requires_research=problem_type == "research",
                requires_planning=problem_type == "planning",
                requires_analysis=problem_type == "analysis",
            )

            for outcome in outcomes:
                self.learner.record(
                    strategy=outcome.strategy,
                    context=context,
                    score=outcome.score,
                    success=outcome.success,
                    improvement=0.0,
                )

    def record(
        self,
        strategy: str,
        context: ProblemContext,
        score: float,
        success: bool,
        improvement: float = 0.0,
    ) -> None:
        from ..models import StrategyOutcome

        outcome = StrategyOutcome(
            strategy=strategy,
            problem_type=context.problem_type,
            score=score,
            success=success,
            metadata={
                "context_aware": True,
                "complexity": context.complexity,
                "keywords": context.keywords,
            },
        )

        self.store.record(outcome)

        self.learner.record(
            strategy=strategy,
            context=context,
            score=score,
            success=success,
            improvement=improvement,
        )

    def choose(
        self,
        context: ProblemContext,
        default_strategy: str = "direct",
    ):
        return self.learner.choose(
            context=context,
            default_strategy=default_strategy,
        )

    def history_count(
        self,
        problem_type: str = "general",
    ) -> int:
        return self.store.count(problem_type)

    def rank(
        self,
        context: ProblemContext,
    ):
        return self.learner.rank(context)
