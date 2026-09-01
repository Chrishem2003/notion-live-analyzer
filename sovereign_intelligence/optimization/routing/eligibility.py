from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..context.models import ProblemContext


@dataclass
class StrategyEligibility:
    strategy: str
    eligible: bool
    reason: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class StrategyEligibilityEngine:
    """Determines which strategies are suitable for a problem context."""

    STRATEGY_RULES = {
        "direct": {
            "types": {
                "general",
                "coding",
                "research",
                "planning",
                "reasoning",
                "analysis",
            },
            "minimum_complexity": 0.0,
        },
        "deep": {
            "types": {
                "general",
                "coding",
                "research",
                "planning",
                "reasoning",
                "analysis",
            },
            "minimum_complexity": 0.30,
        },
        "debug": {
            "types": {
                "coding",
            },
            "minimum_complexity": 0.0,
        },
        "research": {
            "types": {
                "research",
            },
            "minimum_complexity": 0.0,
        },
        "analysis": {
            "types": {
                "analysis",
                "reasoning",
                "coding",
            },
            "minimum_complexity": 0.20,
        },
        "plan": {
            "types": {
                "planning",
            },
            "minimum_complexity": 0.0,
        },
        "verify": {
            "types": {
                "general",
                "coding",
                "research",
                "planning",
                "reasoning",
                "analysis",
            },
            "minimum_complexity": 0.0,
        },
    }

    def evaluate(
        self,
        strategy: str,
        context: ProblemContext,
    ) -> StrategyEligibility:

        if not strategy or not strategy.strip():
            raise ValueError("Strategy cannot be empty.")

        if not 0.0 <= context.complexity <= 1.0:
            raise ValueError(
                "Context complexity must be between 0 and 1."
            )

        strategy = strategy.strip().lower()
        rule = self.STRATEGY_RULES.get(strategy)

        if rule is None:
            return StrategyEligibility(
                strategy=strategy,
                eligible=False,
                reason="Strategy is not registered with the eligibility engine.",
                score=0.0,
                metadata={
                    "known_strategy": False,
                },
            )

        if context.problem_type not in rule["types"]:
            return StrategyEligibility(
                strategy=strategy,
                eligible=False,
                reason=(
                    f"Strategy '{strategy}' is not appropriate for "
                    f"problem type '{context.problem_type}'."
                ),
                score=0.0,
                metadata={
                    "known_strategy": True,
                    "problem_type": context.problem_type,
                },
            )

        minimum_complexity = rule["minimum_complexity"]

        if context.complexity < minimum_complexity:
            return StrategyEligibility(
                strategy=strategy,
                eligible=False,
                reason=(
                    f"Strategy '{strategy}' requires complexity "
                    f">= {minimum_complexity:.2f}."
                ),
                score=0.0,
                metadata={
                    "known_strategy": True,
                    "minimum_complexity": minimum_complexity,
                    "actual_complexity": context.complexity,
                },
            )

        complexity_fit = 1.0

        if minimum_complexity > 0.0:
            complexity_fit = min(
                1.0,
                context.complexity / minimum_complexity,
            )

        return StrategyEligibility(
            strategy=strategy,
            eligible=True,
            reason="Strategy satisfies the context eligibility requirements.",
            score=round(complexity_fit, 4),
            metadata={
                "known_strategy": True,
                "problem_type": context.problem_type,
                "complexity": context.complexity,
                "complexity_fit": round(complexity_fit, 4),
            },
        )

    def eligible_strategies(
        self,
        context: ProblemContext,
        strategies: list[str] | None = None,
    ) -> list[StrategyEligibility]:

        candidates = (
            list(self.STRATEGY_RULES.keys())
            if strategies is None
            else strategies
        )

        results = [
            self.evaluate(strategy, context)
            for strategy in candidates
        ]

        return [
            result
            for result in results
            if result.eligible
        ]

    def all_evaluations(
        self,
        context: ProblemContext,
        strategies: list[str] | None = None,
    ) -> list[StrategyEligibility]:

        candidates = (
            list(self.STRATEGY_RULES.keys())
            if strategies is None
            else strategies
        )

        return [
            self.evaluate(strategy, context)
            for strategy in candidates
        ]
