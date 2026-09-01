from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .constraints import ConstraintEvaluation
from .policy import RoutingPolicy


@dataclass
class RouteScore:
    strategy: str
    score: float
    confidence: float
    historical_score: float
    complexity_fit: float
    constraint_score: float
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


class MultiSignalRouteScorer:
    """Combines multiple routing signals into a single strategy score."""

    def __init__(self, policy: RoutingPolicy | None = None):
        self.policy = policy or RoutingPolicy()

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def complexity_fit(
        strategy: str,
        complexity: float,
    ) -> float:

        if not 0.0 <= complexity <= 1.0:
            raise ValueError(
                "complexity must be between 0 and 1."
            )

        strategy = strategy.strip().lower()

        if strategy == "direct":
            return round(max(0.0, 1.0 - complexity), 4)

        if strategy == "deep":
            return round(complexity, 4)

        if strategy in {"analysis", "debug"}:
            return round(
                min(1.0, complexity + 0.20),
                4,
            )

        if strategy in {"research", "plan", "verify"}:
            return 0.75

        return 0.50

    def score(
        self,
        strategy: str,
        complexity: float,
        confidence: float,
        historical_score: float,
        constraint: ConstraintEvaluation | None = None,
    ) -> RouteScore:

        strategy = strategy.strip().lower()

        if not strategy:
            raise ValueError("Strategy cannot be empty.")

        for name, value in {
            "confidence": confidence,
            "historical_score": historical_score,
        }.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1."
                )

        if not 0.0 <= complexity <= 1.0:
            raise ValueError(
                "complexity must be between 0 and 1."
            )

        if constraint is not None and not constraint.eligible:
            return RouteScore(
                strategy=strategy,
                score=0.0,
                confidence=confidence,
                historical_score=historical_score,
                complexity_fit=0.0,
                constraint_score=0.0,
                reason="Strategy is blocked by routing constraints.",
                metadata={
                    "eligible": False,
                    "blocked": True,
                },
            )

        complexity_signal = self.complexity_fit(
            strategy=strategy,
            complexity=complexity,
        )

        constraint_signal = (
            constraint.preference_score
            if constraint is not None
            else 0.0
        )

        weights = self.policy.normalized_weights()

        score = (
            complexity_signal * weights["complexity"]
            + confidence * weights["confidence"]
            + historical_score * weights["historical"]
            + constraint_signal * weights["constraint"]
        )

        score = round(
            self._clamp(score),
            4,
        )

        return RouteScore(
            strategy=strategy,
            score=score,
            confidence=round(confidence, 4),
            historical_score=round(historical_score, 4),
            complexity_fit=round(complexity_signal, 4),
            constraint_score=round(constraint_signal, 4),
            reason="Route score calculated from multiple routing signals.",
            metadata={
                "eligible": True,
                "weights": weights,
            },
        )

    def rank(
        self,
        candidates: list[dict[str, Any]],
        complexity: float,
    ) -> list[RouteScore]:

        results: list[RouteScore] = []

        for candidate in candidates:
            result = self.score(
                strategy=candidate["strategy"],
                complexity=complexity,
                confidence=float(candidate.get("confidence", 0.0)),
                historical_score=float(
                    candidate.get("historical_score", 0.0)
                ),
                constraint=candidate.get("constraint"),
            )

            if result.score > 0.0:
                results.append(result)

        results.sort(
            key=lambda item: (
                item.score,
                item.confidence,
                item.historical_score,
                item.complexity_fit,
            ),
            reverse=True,
        )

        return results
