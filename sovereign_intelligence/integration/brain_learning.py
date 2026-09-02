from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..models import BrainResult
from ..optimization.autonomous.models import OptimizationResult
from ..optimization.integration import OptimizationLearningEngine


@dataclass
class BrainLearningDecision:
    strategy: str
    problem_type: str
    confidence: float
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BrainLearningAdapter:
    """Safe learning boundary for SovereignBrain.

    The adapter keeps strategy learning separate from the existing
    planning and execution pipeline. Learning failures are isolated
    from the core brain.
    """

    def __init__(
        self,
        database_path: str,
        default_strategy: str = "direct",
    ):
        self.database_path = database_path
        self.default_strategy = default_strategy
        self._engine: OptimizationLearningEngine | None = None

    @property
    def engine(self) -> OptimizationLearningEngine:
        if self._engine is None:
            self._engine = OptimizationLearningEngine(
                database_path=self.database_path
            )
        return self._engine

    def choose_strategy(
        self,
        problem_type: str = "general",
    ) -> BrainLearningDecision:
        try:
            decision = self.engine.choose_next_strategy(
                problem_type=problem_type,
                default_strategy=self.default_strategy,
            )

            return BrainLearningDecision(
                strategy=decision.strategy,
                problem_type=decision.problem_type,
                confidence=decision.confidence,
                reason=decision.reason,
                metadata={
                    "learning_available": True,
                    "ranked_candidates": len(decision.ranked),
                },
            )

        except Exception as exc:
            return BrainLearningDecision(
                strategy=self.default_strategy,
                problem_type=problem_type,
                confidence=0.0,
                reason="Learning subsystem unavailable; using default strategy.",
                metadata={
                    "learning_available": False,
                    "error": str(exc),
                },
            )

    def ranked_strategies(
        self,
        problem_type: str = "general",
    ) -> list[Any]:
        """Return historically ranked strategies safely.

        This is intentionally best-effort so learning failures never
        break the core SovereignBrain execution path.
        """
        try:
            decision = self.engine.choose_next_strategy(
                problem_type=problem_type,
                default_strategy=self.default_strategy,
            )
            return list(
                getattr(
                    decision,
                    "ranked",
                    [],
                )
                or []
            )
        except Exception:
            return []
    def record_optimization(
        self,
        optimization: OptimizationResult,
        success: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        try:
            return self.engine.process(
                optimization=optimization,
                success=success,
                metadata=metadata,
                default_strategy=self.default_strategy,
            )
        except Exception:
            return None

    def record_brain_result(
        self,
        result: BrainResult,
        problem_type: str = "general",
        baseline_score: float = 0.5,
        metadata: dict[str, Any] | None = None,
        strategy: str | None = None,
    ):
        score = 1.0 if result.verification and result.verification.passed else baseline_score

        actual_strategy = (
            str(strategy).strip().lower()
            if strategy
            else self.default_strategy
        )

        optimization = OptimizationResult(
            strategy=actual_strategy,
            problem_type=problem_type,
            previous_score=baseline_score,
            new_score=score,
            improvement=score - baseline_score,
            optimized=False,
            confidence=(
                result.verification.confidence
                if result.verification
                else 0.0
            ),
            candidates=[],
            metadata={
                "source": "sovereign_brain",
                "provider": result.provider,
                "model": result.model,
                "strategy": actual_strategy,
                **(metadata or {}),
            },
        )

        return self.record_optimization(
            optimization=optimization,
            success=score >= baseline_score,
            metadata=optimization.metadata,
        )
