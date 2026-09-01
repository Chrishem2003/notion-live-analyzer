from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..autonomous.models import OptimizationResult
from ..feedback.models import StrategyFeedback
from ..learning.models import LearningDecision
from .feedback_bridge import OptimizationFeedbackBridge
from .persistent_feedback import PersistentFeedbackLearner


@dataclass
class ClosedLoopResult:
    optimization: OptimizationResult
    feedback: StrategyFeedback
    next_decision: LearningDecision
    metadata: dict[str, Any] = field(default_factory=dict)


class ClosedLoopOptimizationController:
    """Connect optimization, feedback, persistence, and learning."""

    def __init__(
        self,
        feedback_bridge: OptimizationFeedbackBridge,
        persistent_learner: PersistentFeedbackLearner,
    ):
        self.feedback_bridge = feedback_bridge
        self.persistent_learner = persistent_learner

    def process(
        self,
        optimization: OptimizationResult,
        success: bool | None = None,
        metadata: dict[str, Any] | None = None,
        default_strategy: str = "direct",
    ) -> ClosedLoopResult:
        feedback = self.feedback_bridge.create_feedback(
            result=optimization,
            success=success,
            metadata=metadata,
        )

        self.persistent_learner.record(feedback)

        next_decision = self.persistent_learner.choose(
            problem_type=optimization.problem_type,
            default_strategy=default_strategy,
        )

        return ClosedLoopResult(
            optimization=optimization,
            feedback=feedback,
            next_decision=next_decision,
            metadata={
                "feedback_recorded": True,
                "next_strategy": next_decision.strategy,
                "next_confidence": next_decision.confidence,
            },
        )
