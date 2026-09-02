from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .controller import AdaptiveExecutionController
from .evaluator import IntermediateResultAssessment
from .monitor import ExecutionProgressMonitor, ProgressAssessment


@dataclass
class StrategySwitchDecision:
    """Decision describing whether execution should switch strategy."""

    switch: bool
    current_strategy: str
    selected_strategy: str
    reason: str

    monitor_assessment: ProgressAssessment | None = None
    result_assessment: IntermediateResultAssessment | None = None

    alternatives: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)


class DynamicStrategySwitcher:
    """Coordinates execution monitoring and adaptive strategy switching."""

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
        *,
        monitor: ExecutionProgressMonitor | None = None,
        evaluator=None,
        minimum_switch_confidence: float = 0.50,
    ):
        if not 0.0 <= minimum_switch_confidence <= 1.0:
            raise ValueError(
                "minimum_switch_confidence must be between 0 and 1."
            )

        self.monitor = monitor or ExecutionProgressMonitor()
        self.evaluator = evaluator
        self.minimum_switch_confidence = (
            minimum_switch_confidence
        )

    @classmethod
    def _route_for_strategy(
        cls,
        strategy: str,
    ) -> str:
        return cls.ROUTE_MAP.get(
            strategy,
            f"{strategy}_execution",
        )

    @staticmethod
    def _default_alternatives(
        current_strategy: str,
    ) -> list[str]:
        fallback_map = {
            "direct": ["deep", "analysis", "verify"],
            "deep": ["analysis", "verify", "direct"],
            "debug": ["deep", "analysis", "verify"],
            "research": ["analysis", "deep", "verify"],
            "analysis": ["deep", "verify", "direct"],
            "plan": ["deep", "direct", "verify"],
            "verify": ["deep", "analysis", "direct"],
        }

        return fallback_map.get(
            current_strategy,
            ["deep", "analysis", "verify"],
        )

    def evaluate(
        self,
        controller: AdaptiveExecutionController,
        *,
        result: str = "",
        objective: str = "",
        strategy_candidates: list[str] | None = None,
    ) -> StrategySwitchDecision:

        state = controller.state

        current_strategy = state.strategy

        monitor_assessment = self.monitor.assess(
            state
        )

        result_assessment = None

        if self.evaluator is not None:
            result_assessment = self.evaluator.evaluate(
                result,
                objective=objective,
            )

        needs_switch = (
            monitor_assessment.needs_reassessment
            or (
                result_assessment is not None
                and result_assessment.needs_reassessment
            )
        )

        if not needs_switch:
            return StrategySwitchDecision(
                switch=False,
                current_strategy=current_strategy,
                selected_strategy=current_strategy,
                reason=(
                    "Current execution remains healthy; "
                    "strategy switch is not required."
                ),
                monitor_assessment=monitor_assessment,
                result_assessment=result_assessment,
            )

        candidates = (
            list(strategy_candidates)
            if strategy_candidates is not None
            else self._default_alternatives(
                current_strategy
            )
        )

        candidates = [
            strategy
            for strategy in candidates
            if strategy
            and strategy != current_strategy
        ]

        if not candidates:
            return StrategySwitchDecision(
                switch=False,
                current_strategy=current_strategy,
                selected_strategy=current_strategy,
                reason=(
                    "Execution requires reassessment, "
                    "but no alternative strategy is available."
                ),
                monitor_assessment=monitor_assessment,
                result_assessment=result_assessment,
            )

        selected_strategy = candidates[0]

        confidence = monitor_assessment.confidence

        if result_assessment is not None:
            confidence = min(
                confidence,
                result_assessment.confidence,
            )

        if confidence < self.minimum_switch_confidence:
            return StrategySwitchDecision(
                switch=False,
                current_strategy=current_strategy,
                selected_strategy=current_strategy,
                reason=(
                    "Execution requires reassessment, but "
                    "confidence is too low to switch automatically."
                ),
                monitor_assessment=monitor_assessment,
                result_assessment=result_assessment,
                alternatives=candidates,
                metadata={
                    "switch_confidence": confidence,
                    "minimum_switch_confidence": (
                        self.minimum_switch_confidence
                    ),
                },
            )

        return StrategySwitchDecision(
            switch=True,
            current_strategy=current_strategy,
            selected_strategy=selected_strategy,
            reason=(
                f"Switching from '{current_strategy}' to "
                f"'{selected_strategy}' because execution "
                "quality requires reassessment."
            ),
            monitor_assessment=monitor_assessment,
            result_assessment=result_assessment,
            alternatives=candidates[1:],
            metadata={
                "switch_confidence": confidence,
                "minimum_switch_confidence": (
                    self.minimum_switch_confidence
                ),
                "selected_route": self._route_for_strategy(
                    selected_strategy
                ),
            },
        )

    def apply(
        self,
        controller: AdaptiveExecutionController,
        decision: StrategySwitchDecision,
    ):
        if not decision.switch:
            return controller.snapshot()

        selected_strategy = decision.selected_strategy

        selected_route = self._route_for_strategy(
            selected_strategy
        )

        controller.switch_strategy(
            selected_strategy,
            selected_route,
        )

        return controller.snapshot()


__all__ = [
    "StrategySwitchDecision",
    "DynamicStrategySwitcher",
]
