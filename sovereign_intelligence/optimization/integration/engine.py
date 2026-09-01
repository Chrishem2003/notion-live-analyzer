from __future__ import annotations

from ..autonomous.models import OptimizationResult
from ..feedback.engine import FeedbackEngine
from ..persistent import PersistentStrategyStore
from .closed_loop import ClosedLoopOptimizationController, ClosedLoopResult
from .feedback_bridge import OptimizationFeedbackBridge
from .persistent_feedback import PersistentFeedbackLearner


class OptimizationLearningEngine:
    """Public Stage 40 engine for optimization-to-learning feedback."""

    def __init__(self, database_path: str):
        self.store = PersistentStrategyStore(database_path)

        self.feedback_engine = FeedbackEngine()

        self.bridge = OptimizationFeedbackBridge(
            feedback_engine=self.feedback_engine
        )

        self.learner = PersistentFeedbackLearner(
            store=self.store
        )

        self.controller = ClosedLoopOptimizationController(
            feedback_bridge=self.bridge,
            persistent_learner=self.learner,
        )

    def process(
        self,
        optimization: OptimizationResult,
        success: bool | None = None,
        metadata: dict | None = None,
        default_strategy: str = "direct",
    ) -> ClosedLoopResult:
        return self.controller.process(
            optimization=optimization,
            success=success,
            metadata=metadata,
            default_strategy=default_strategy,
        )

    def choose_next_strategy(
        self,
        problem_type: str = "general",
        default_strategy: str = "direct",
    ):
        return self.learner.choose(
            problem_type=problem_type,
            default_strategy=default_strategy,
        )

    def history_count(
        self,
        problem_type: str = "general",
    ) -> int:
        return self.learner.history_count(problem_type)
