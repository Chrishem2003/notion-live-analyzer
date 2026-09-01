from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .decision import DynamicRouteDecision


@dataclass
class RouteExplanation:
    strategy: str
    route: str
    summary: str
    factors: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    fallback: bool = False
    trace: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class RouteExplanationEngine:
    """Builds an auditable explanation for a dynamic route decision."""

    def explain(
        self,
        decision: DynamicRouteDecision,
    ) -> RouteExplanation:

        factors: list[str] = []
        trace: list[dict[str, Any]] = []

        ranked = decision.ranked_strategies

        winner = decision.strategy

        if decision.fallback_used:
            factors.append(
                "The routing policy selected the configured fallback strategy."
            )

            trace.append(
                {
                    "event": "fallback",
                    "strategy": winner,
                    "reason": decision.reason,
                }
            )
        else:
            factors.append(
                f"Strategy '{winner}' was selected as the highest-scoring eligible route."
            )

            trace.append(
                {
                    "event": "winner_selected",
                    "strategy": winner,
                    "score": decision.score,
                    "confidence": decision.confidence,
                }
            )

        factors.append(
            f"Problem type: {decision.problem_type}."
        )

        factors.append(
            f"Complexity: {decision.complexity:.4f} "
            f"({decision.complexity_band} band)."
        )

        if ranked:
            winner_entry = next(
                (
                    item
                    for item in ranked
                    if item.get("strategy") == winner
                ),
                None,
            )

            if winner_entry:
                complexity_fit = winner_entry.get(
                    "complexity_fit",
                    0.0,
                )

                historical_score = winner_entry.get(
                    "historical_score",
                    0.0,
                )

                constraint_score = winner_entry.get(
                    "constraint_score",
                    0.0,
                )

                factors.append(
                    f"Complexity fit: {complexity_fit:.4f}."
                )

                factors.append(
                    f"Historical score: {historical_score:.4f}."
                )

                factors.append(
                    f"Constraint score: {constraint_score:.4f}."
                )

                trace.append(
                    {
                        "event": "winner_signals",
                        "strategy": winner,
                        "complexity_fit": complexity_fit,
                        "historical_score": historical_score,
                        "constraint_score": constraint_score,
                    }
                )

        alternatives = [
            str(item.get("strategy"))
            for item in ranked
            if item.get("strategy") != winner
        ]

        for item in ranked:
            trace.append(
                {
                    "event": "candidate",
                    "strategy": item.get("strategy"),
                    "score": item.get("score"),
                    "confidence": item.get("confidence"),
                    "historical_score": item.get(
                        "historical_score"
                    ),
                    "complexity_fit": item.get(
                        "complexity_fit"
                    ),
                    "constraint_score": item.get(
                        "constraint_score"
                    ),
                }
            )

        summary = (
            f"Selected '{winner}' via route '{decision.route}' "
            f"for a {decision.problem_type} problem with "
            f"{decision.complexity_band} complexity."
        )

        return RouteExplanation(
            strategy=winner,
            route=decision.route,
            summary=summary,
            factors=factors,
            alternatives=alternatives,
            fallback=decision.fallback_used,
            trace=trace,
            metadata={
                "decision_score": decision.score,
                "decision_confidence": decision.confidence,
                "candidate_count": len(ranked),
                "dynamic_routing": True,
            },
        )
