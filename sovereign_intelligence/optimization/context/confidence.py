from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .router import ContextStrategyRouter, StrategyRoute


@dataclass
class ConfidenceAwareRoute:
    strategy: str
    route: str
    problem_type: str
    complexity: float
    complexity_band: str
    confidence: float
    fallback_used: bool
    reason: str
    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class ConfidenceAwareStrategyRouter:
    """
    Strategy router that refuses to blindly trust
    low-confidence historical learning.
    """

    def __init__(
        self,
        minimum_confidence: float = 0.67,
        minimum_samples: int = 3,
    ):
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError(
                "minimum_confidence must be between 0 and 1."
            )

        self.minimum_confidence = (
            minimum_confidence
        )

        self.router = ContextStrategyRouter(
            minimum_samples=minimum_samples
        )

    def classify(self, prompt: str):
        return self.router.classify(prompt)

    def record(
        self,
        strategy: str,
        context,
        score: float,
        success: bool,
        improvement: float = 0.0,
    ) -> None:
        self.router.record(
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
        fallback_strategy: str = "direct",
    ) -> ConfidenceAwareRoute:

        base_route: StrategyRoute = self.router.route(
            prompt=prompt,
            default_strategy=default_strategy,
        )

        if (
            base_route.confidence
            >= self.minimum_confidence
        ):
            return ConfidenceAwareRoute(
                strategy=base_route.strategy,
                route=base_route.route,
                problem_type=base_route.problem_type,
                complexity=base_route.complexity,
                complexity_band=base_route.complexity_band,
                confidence=base_route.confidence,
                fallback_used=False,
                reason=(
                    "Historical strategy evidence "
                    "exceeded the confidence threshold."
                ),
                metadata={
                    **base_route.metadata,
                    "confidence_threshold": (
                        self.minimum_confidence
                    ),
                    "fallback_used": False,
                },
            )

        route_map = {
            "direct": "standard_execution",
            "deep": "deep_reasoning_execution",
            "verify": "verified_execution",
            "research": "research_execution",
            "analysis": "analytical_execution",
            "debug": "debug_execution",
            "plan": "planning_execution",
        }

        fallback_route = route_map.get(
            fallback_strategy,
            "standard_execution",
        )

        return ConfidenceAwareRoute(
            strategy=fallback_strategy,
            route=fallback_route,
            problem_type=base_route.problem_type,
            complexity=base_route.complexity,
            complexity_band=base_route.complexity_band,
            confidence=base_route.confidence,
            fallback_used=True,
            reason=(
                "Historical evidence was below the "
                "confidence threshold; using the "
                "configured safe fallback strategy."
            ),
            metadata={
                **base_route.metadata,
                "confidence_threshold": (
                    self.minimum_confidence
                ),
                "fallback_used": True,
                "original_strategy": (
                    base_route.strategy
                ),
            },
        )

    def count(self) -> int:
        return self.router.count()

    def clear(self) -> None:
        self.router.clear()
