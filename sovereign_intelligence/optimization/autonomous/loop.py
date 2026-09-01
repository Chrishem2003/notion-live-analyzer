from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .optimizer import AutonomousOptimizer


@dataclass
class OptimizationIteration:
    iteration: int
    strategy: str
    score: float
    improvement: float
    optimized: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationLoopResult:
    strategy: str
    score: float
    iterations: int
    improved: bool
    stopped_reason: str
    history: list[OptimizationIteration] = field(
        default_factory=list
    )


class AutonomousOptimizationLoop:
    """
    Controlled feedback loop for autonomous strategy optimization.

    The loop does not execute providers or tools itself.
    The caller supplies an execution callback.
    """

    def __init__(
        self,
        optimizer: AutonomousOptimizer | None = None,
        max_iterations: int = 3,
    ):
        if max_iterations < 1:
            raise ValueError(
                "max_iterations must be at least 1."
            )

        self.optimizer = optimizer or AutonomousOptimizer()
        self.max_iterations = max_iterations

    def run(
        self,
        problem_type: str,
        current_strategy: str,
        current_score: float,
        ranked,
        execute: Callable[[str], float],
    ) -> OptimizationLoopResult:

        if not problem_type.strip():
            raise ValueError(
                "problem_type cannot be empty."
            )

        if not current_strategy.strip():
            raise ValueError(
                "current_strategy cannot be empty."
            )

        if not 0 <= current_score <= 1:
            raise ValueError(
                "current_score must be between 0 and 1."
            )

        if not callable(execute):
            raise TypeError(
                "execute must be callable."
            )

        strategy = current_strategy
        score = current_score
        history = []
        improved = False
        stopped_reason = "maximum_iterations"

        for iteration in range(1, self.max_iterations + 1):

            decision = self.optimizer.optimize(
                current_strategy=strategy,
                current_score=score,
                ranked=ranked,
                problem_type=problem_type,
            )

            if not decision.optimized:
                history.append(
                    OptimizationIteration(
                        iteration=iteration,
                        strategy=strategy,
                        score=round(score, 4),
                        improvement=0.0,
                        optimized=False,
                        metadata={
                            "reason": decision.metadata.get(
                                "reason",
                                "No sufficient improvement.",
                            )
                        },
                    )
                )

                stopped_reason = "no_sufficient_improvement"
                break

            candidate_strategy = decision.strategy

            new_score = execute(candidate_strategy)

            if not 0 <= new_score <= 1:
                raise ValueError(
                    "Execution callback must return a score "
                    "between 0 and 1."
                )

            improvement = new_score - score

            history.append(
                OptimizationIteration(
                    iteration=iteration,
                    strategy=candidate_strategy,
                    score=round(new_score, 4),
                    improvement=round(
                        improvement,
                        4,
                    ),
                    optimized=True,
                )
            )

            if improvement <= 0:
                stopped_reason = "improvement_stalled"
                break

            improved = True
            strategy = candidate_strategy
            score = new_score

            if improvement < self.optimizer.minimum_improvement:
                stopped_reason = "minimum_improvement_reached"
                break

        return OptimizationLoopResult(
            strategy=strategy,
            score=round(score, 4),
            iterations=len(history),
            improved=improved,
            stopped_reason=stopped_reason,
            history=history,
        )
