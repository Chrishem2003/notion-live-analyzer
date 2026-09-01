from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..context.models import ProblemContext
from .constraint_router import ConstraintAwareRouter
from .policy import RoutingPolicy
from .constraints import RoutingConstraints
from .scoring import MultiSignalRouteScorer


@dataclass
class DynamicRouteDecision:
    strategy: str
    route: str
    problem_type: str
    complexity: float
    complexity_band: str
    score: float
    confidence: float
    fallback_used: bool
    reason: str
    ranked_strategies: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class DynamicRouteDecisionEngine:
    """Selects the best currently eligible execution strategy."""

    ROUTE_MAP = {
        "direct": "standard_execution",
        "deep": "deep_reasoning_execution",
        "verify": "verified_execution",
        "research": "research_execution",
        "analysis": "analytical_execution",
        "debug": "debug_execution",
        "plan": "planning_execution",
    }

    def __init__(
        self,
        policy: RoutingPolicy | None = None,
    ):
        self.policy = policy or RoutingPolicy()
        self.constraint_router = ConstraintAwareRouter()
        self.scorer = MultiSignalRouteScorer(
            policy=self.policy
        )

    @staticmethod
    def complexity_band(complexity: float) -> str:
        if not 0.0 <= complexity <= 1.0:
            raise ValueError(
                "complexity must be between 0 and 1."
            )

        if complexity < 0.34:
            return "low"

        if complexity < 0.67:
            return "medium"

        return "high"

    def decide(
        self,
        context: ProblemContext,
        candidates: list[dict[str, Any]],
        constraints: RoutingConstraints | None = None,
        default_strategy: str = "direct",
    ) -> DynamicRouteDecision:

        if not candidates:
            return self._fallback_decision(
                context=context,
                default_strategy=default_strategy,
                reason="No routing candidates were provided.",
            )

        constraints = constraints or RoutingConstraints()

        evaluated: list[dict[str, Any]] = []

        for candidate in candidates:
            strategy = str(
                candidate.get("strategy", "")
            ).strip().lower()

            if not strategy:
                continue

            confidence = float(
                candidate.get("confidence", 0.0)
            )

            historical_score = float(
                candidate.get("historical_score", 0.0)
            )

            constraint_result = self.constraint_router.evaluate(
                strategy=strategy,
                context=context,
                constraints=constraints,
                confidence=confidence,
            )

            route_score = self.scorer.score(
                strategy=strategy,
                complexity=context.complexity,
                confidence=confidence,
                historical_score=historical_score,
                constraint=constraint_result,
            )

            if route_score.score <= 0.0:
                continue

            evaluated.append(
                {
                    "strategy": strategy,
                    "route": self.ROUTE_MAP.get(
                        strategy,
                        "standard_execution",
                    ),
                    "score": route_score.score,
                    "confidence": route_score.confidence,
                    "historical_score": route_score.historical_score,
                    "complexity_fit": route_score.complexity_fit,
                    "constraint_score": route_score.constraint_score,
                    "reason": route_score.reason,
                }
            )

        evaluated.sort(
            key=lambda item: (
                item["score"],
                item["confidence"],
                item["historical_score"],
            ),
            reverse=True,
        )

        if not evaluated:
            return self._fallback_decision(
                context=context,
                default_strategy=default_strategy,
                reason=(
                    "No candidate satisfied the routing constraints; "
                    "using the configured fallback strategy."
                ),
            )

        winner = evaluated[0]

        if self.policy.requires_fallback(
            winner["confidence"]
        ):
            return self._fallback_decision(
                context=context,
                default_strategy=self.policy.fallback_strategy,
                reason=(
                    "Winning strategy confidence was below "
                    "the routing policy threshold."
                ),
                ranked=evaluated,
                original_strategy=winner["strategy"],
                original_score=winner["score"],
                original_confidence=winner["confidence"],
            )

        return DynamicRouteDecision(
            strategy=winner["strategy"],
            route=winner["route"],
            problem_type=context.problem_type,
            complexity=context.complexity,
            complexity_band=self.complexity_band(
                context.complexity
            ),
            score=winner["score"],
            confidence=winner["confidence"],
            fallback_used=False,
            reason=(
                "Selected the highest-scoring eligible strategy "
                "using multi-signal routing."
            ),
            ranked_strategies=evaluated,
            metadata={
                "dynamic_routing": True,
                "candidate_count": len(evaluated),
                "fallback_used": False,
            },
        )

    def _fallback_decision(
        self,
        context: ProblemContext,
        default_strategy: str,
        reason: str,
        ranked: list[dict[str, Any]] | None = None,
        original_strategy: str | None = None,
        original_score: float = 0.0,
        original_confidence: float = 0.0,
    ) -> DynamicRouteDecision:

        strategy = (
            self.policy.fallback_strategy
            if self.policy.allow_fallback
            else default_strategy
        )

        strategy = strategy.strip().lower()

        return DynamicRouteDecision(
            strategy=strategy,
            route=self.ROUTE_MAP.get(
                strategy,
                "standard_execution",
            ),
            problem_type=context.problem_type,
            complexity=context.complexity,
            complexity_band=self.complexity_band(
                context.complexity
            ),
            score=0.0,
            confidence=original_confidence,
            fallback_used=True,
            reason=reason,
            ranked_strategies=ranked or [],
            metadata={
                "dynamic_routing": True,
                "fallback_used": True,
                "original_strategy": original_strategy,
                "original_score": original_score,
            },
        )


