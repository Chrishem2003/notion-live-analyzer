from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..learning.learner import StrategyLearner
from ..learning.models import StrategyScore
from .models import ProblemContext


@dataclass
class ContextLearningDecision:
    strategy: str
    problem_type: str
    confidence: float
    reason: str
    complexity: float
    ranked: list[StrategyScore] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextAwareStrategyLearner:
    """Select strategies using both problem context and historical learning."""

    def __init__(
        self,
        minimum_samples: int = 3,
    ):
        self.learner = StrategyLearner(
            minimum_samples=minimum_samples
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
            problem_type=context.problem_type,
            score=score,
            success=success,
            improvement=improvement,
        )

    def rank(
        self,
        context: ProblemContext,
    ) -> list[StrategyScore]:
        ranked = self.learner.rank(
            context.problem_type
        )

        return ranked

    def choose(
        self,
        context: ProblemContext,
        default_strategy: str = "direct",
    ) -> ContextLearningDecision:
        ranked = self.rank(context)

        if not ranked:
            return ContextLearningDecision(
                strategy=default_strategy,
                problem_type=context.problem_type,
                confidence=0.0,
                reason=(
                    "No historical evidence for this problem "
                    "context; using the default strategy."
                ),
                complexity=context.complexity,
                ranked=[],
                metadata={
                    "historical_evidence": False,
                    "context_aware": True,
                },
            )

        winner = ranked[0]

        return ContextLearningDecision(
            strategy=winner.strategy,
            problem_type=context.problem_type,
            confidence=winner.confidence,
            reason=(
                "Selected using historical performance "
                "for the detected problem context."
            ),
            complexity=context.complexity,
            ranked=ranked,
            metadata={
                "historical_evidence": True,
                "context_aware": True,
                "candidate_count": len(ranked),
            },
        )

    def count(self) -> int:
        return self.learner.count()

    def clear(self) -> None:
        self.learner.clear()
