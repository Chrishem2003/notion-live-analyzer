from __future__ import annotations

from ..autonomous.models import OptimizationResult
from ..feedback.engine import FeedbackEngine
from ..feedback.models import StrategyFeedback


class OptimizationFeedbackBridge:
    """Convert autonomous optimization results into strategy feedback."""

    def __init__(self, feedback_engine: FeedbackEngine | None = None):
        self.feedback_engine = feedback_engine or FeedbackEngine()

    def create_feedback(
        self,
        result: OptimizationResult,
        success: bool | None = None,
        metadata: dict | None = None,
    ) -> StrategyFeedback:
        if not result.problem_type.strip():
            raise ValueError("Optimization result must contain a problem type.")

        if success is None:
            success = result.new_score >= result.previous_score

        combined_metadata = {
            "optimized": result.optimized,
            "optimization_confidence": result.confidence,
            "optimization_improvement": result.improvement,
            "selected_strategy": result.strategy,
        }

        if result.metadata:
            combined_metadata.update(result.metadata)

        if metadata:
            combined_metadata.update(metadata)

        return self.feedback_engine.evaluate(
            strategy=result.strategy,
            problem_type=result.problem_type,
            baseline_score=result.previous_score,
            final_score=result.new_score,
            success=bool(success),
            metadata=combined_metadata,
        )
