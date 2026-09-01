from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .classifier import ProblemContextClassifier
from .complexity import ComplexityAwareStrategyLearner
from .models import ProblemContext


@dataclass
class StrategyRoute:
    strategy: str
    problem_type: str
    complexity: float
    complexity_band: str
    confidence: float
    route: str
    reason: str
    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class ContextStrategyRouter:
    """
    Convert a raw problem into an executable strategy route.

    This layer does not execute the strategy.
    It only determines the safest learned route.
    """

    def __init__(
        self,
        minimum_samples: int = 3,
    ):
        self.classifier = ProblemContextClassifier()

        self.learner = ComplexityAwareStrategyLearner(
            minimum_samples=minimum_samples
        )

    def classify(
        self,
        prompt: str,
    ) -> ProblemContext:
        return self.classifier.classify(
            prompt
        )

    def record(
        self,
        strategy: str,
        context: ProblemContext,
        score: float,
        success: bool,
        improvement: float = 0.0,
    ) -> None:
        self.learner.record(
            strategy=strategy,
            context=context,
            score=score,
            success=success,
            improvement=improvement,
        )

    def route(
        self,
        prompt: str,
        default_strategy: str = "direct",
    ) -> StrategyRoute:

        context = self.classify(
            prompt
        )

        decision = self.learner.choose(
            context=context,
            default_strategy=default_strategy,
        )

        strategy = decision.strategy

        route_map = {
            "direct": "standard_execution",
            "deep": "deep_reasoning_execution",
            "verify": "verified_execution",
            "research": "research_execution",
            "analysis": "analytical_execution",
            "debug": "debug_execution",
            "plan": "planning_execution",
        }

        execution_route = route_map.get(
            strategy,
            "standard_execution",
        )

        return StrategyRoute(
            strategy=strategy,
            problem_type=context.problem_type,
            complexity=context.complexity,
            complexity_band=decision.complexity_band,
            confidence=decision.confidence,
            route=execution_route,
            reason=decision.reason,
            metadata={
                "context_aware": True,
                "complexity_aware": True,
                "historical_evidence": decision.metadata.get(
                    "historical_evidence",
                    False,
                ),
                "candidate_count": decision.metadata.get(
                    "candidate_count",
                    0,
                ),
            },
        )

    def count(self) -> int:
        return self.learner.count()

    def clear(self) -> None:
        self.learner.clear()
