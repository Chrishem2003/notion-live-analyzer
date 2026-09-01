from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..context.models import ProblemContext
from .constraints import RoutingConstraints
from .decision import (
    DynamicRouteDecision,
    DynamicRouteDecisionEngine,
)


@dataclass
class RouteFailure:
    strategy: str
    reason: str
    recoverable: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FailureAdjustment:
    previous_strategy: str
    selected_strategy: str
    changed: bool
    reason: str
    failed_strategies: list[str] = field(default_factory=list)
    decision: DynamicRouteDecision | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class FailureAwareRouteAdjuster:
    """Adjusts routing after a strategy execution failure."""

    def __init__(
        self,
        decision_engine: DynamicRouteDecisionEngine | None = None,
    ):
        self.decision_engine = (
            decision_engine
            or DynamicRouteDecisionEngine()
        )

    def adjust(
        self,
        context: ProblemContext,
        candidates: list[dict[str, Any]],
        failure: RouteFailure,
        constraints: RoutingConstraints | None = None,
        default_strategy: str = "direct",
    ) -> FailureAdjustment:

        failed_strategy = (
            failure.strategy.strip().lower()
        )

        if not failed_strategy:
            raise ValueError(
                "Failure strategy cannot be empty."
            )

        remaining = []

        for candidate in candidates:
            strategy = str(
                candidate.get("strategy", "")
            ).strip().lower()

            if not strategy:
                continue

            if strategy == failed_strategy:
                continue

            remaining.append(candidate)

        constraints = constraints or RoutingConstraints()

        adjusted_constraints = RoutingConstraints(
            required_capabilities=set(
                constraints.required_capabilities
            ),
            forbidden_strategies=set(
                constraints.forbidden_strategies
            ) | {failed_strategy},
            preferred_strategies=list(
                constraints.preferred_strategies
            ),
            minimum_confidence=constraints.minimum_confidence,
            maximum_complexity=constraints.maximum_complexity,
            metadata={
                **constraints.metadata,
                "failure_adjustment": True,
                "failed_strategy": failed_strategy,
                "failure_reason": failure.reason,
            },
        )

        if not remaining:
            return FailureAdjustment(
                previous_strategy=failed_strategy,
                selected_strategy=default_strategy,
                changed=(
                    failed_strategy
                    != default_strategy
                ),
                reason=(
                    "The failed strategy was excluded, but no "
                    "alternative candidates remained."
                ),
                failed_strategies=[
                    failed_strategy
                ],
                decision=None,
                metadata={
                    "failure_adjustment": True,
                    "recoverable": failure.recoverable,
                    "no_alternatives": True,
                },
            )

        decision = self.decision_engine.decide(
            context=context,
            candidates=remaining,
            constraints=adjusted_constraints,
            default_strategy=default_strategy,
        )

        return FailureAdjustment(
            previous_strategy=failed_strategy,
            selected_strategy=decision.strategy,
            changed=(
                decision.strategy
                != failed_strategy
            ),
            reason=(
                "Failed strategy was excluded and routing "
                "was recalculated using the remaining candidates."
            ),
            failed_strategies=[
                failed_strategy
            ],
            decision=decision,
            metadata={
                "failure_adjustment": True,
                "recoverable": failure.recoverable,
                "remaining_candidates": len(remaining),
            },
        )
