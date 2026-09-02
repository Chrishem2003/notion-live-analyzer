from __future__ import annotations

from typing import Any, Mapping

from ...observability.trace import Trace
from .state import ExecutionState, ExecutionStatus


class AdaptiveExecutionTrace:
    """
    Trace adapter for adaptive execution orchestration.

    This class does not replace the platform Trace implementation.
    It translates adaptive execution lifecycle events into the
    existing Trace.event(...) interface.
    """

    def __init__(self, trace: Trace | None = None) -> None:
        self.trace = trace or Trace()

    @staticmethod
    def _status_value(status: Any) -> str:
        if isinstance(status, ExecutionStatus):
            return status.value

        return str(status)

    @staticmethod
    def _state_metadata(
        state: ExecutionState,
    ) -> dict[str, Any]:
        return {
            "execution_id": state.execution_id,
            "strategy": state.strategy,
            "route": state.route,
            "problem_type": state.problem_type,
            "status": AdaptiveExecutionTrace._status_value(
                state.status
            ),
            "progress": state.progress,
            "attempt": state.attempt,
            "completed_steps": state.completed_steps,
            "total_steps": state.total_steps,
            "intermediate_score": state.intermediate_score,
            "confidence": state.confidence,
        }

    def record(
        self,
        name: str,
        state: ExecutionState,
        **metadata: Any,
    ) -> None:
        payload = self._state_metadata(state)
        payload.update(metadata)
        self.trace.event(name, **payload)

    def execution_created(
        self,
        state: ExecutionState,
        **metadata: Any,
    ) -> None:
        self.record(
            "adaptive.execution.created",
            state,
            **metadata,
        )

    def execution_started(
        self,
        state: ExecutionState,
        **metadata: Any,
    ) -> None:
        self.record(
            "adaptive.execution.started",
            state,
            **metadata,
        )

    def progress_updated(
        self,
        state: ExecutionState,
        **metadata: Any,
    ) -> None:
        self.record(
            "adaptive.execution.progress_updated",
            state,
            **metadata,
        )

    def result_evaluated(
        self,
        state: ExecutionState,
        *,
        score: float | None = None,
        confidence: float | None = None,
        needs_reassessment: bool | None = None,
        **metadata: Any,
    ) -> None:
        self.record(
            "adaptive.execution.result_evaluated",
            state,
            score=score,
            evaluation_confidence=confidence,
            needs_reassessment=needs_reassessment,
            **metadata,
        )

    def strategy_switched(
        self,
        state: ExecutionState,
        *,
        previous_strategy: str,
        previous_route: str,
        reason: str | None = None,
        **metadata: Any,
    ) -> None:
        self.record(
            "adaptive.execution.strategy_switched",
            state,
            previous_strategy=previous_strategy,
            previous_route=previous_route,
            reason=reason,
            strategy_history=list(state.strategy_history),
            strategy_switch_count=state.strategy_switch_count,
            **metadata,
        )

    def recovery_started(
        self,
        state: ExecutionState,
        *,
        reason: str,
        **metadata: Any,
    ) -> None:
        self.record(
            "adaptive.execution.recovery_started",
            state,
            reason=reason,
            **metadata,
        )

    def recovery_applied(
        self,
        state: ExecutionState,
        *,
        action: str,
        reason: str | None = None,
        **metadata: Any,
    ) -> None:
        self.record(
            "adaptive.execution.recovery_applied",
            state,
            action=action,
            reason=reason,
            **metadata,
        )

    def execution_failed(
        self,
        state: ExecutionState,
        *,
        reason: str,
        **metadata: Any,
    ) -> None:
        self.record(
            "adaptive.execution.failed",
            state,
            reason=reason,
            **metadata,
        )

    def execution_completed(
        self,
        state: ExecutionState,
        **metadata: Any,
    ) -> None:
        self.record(
            "adaptive.execution.completed",
            state,
            **metadata,
        )

    def execution_cancelled(
        self,
        state: ExecutionState,
        *,
        reason: str | None = None,
        **metadata: Any,
    ) -> None:
        self.record(
            "adaptive.execution.cancelled",
            state,
            reason=reason,
            **metadata,
        )

    def export(self) -> list[dict[str, Any]]:
        return self.trace.export()


__all__ = [
    "AdaptiveExecutionTrace",
]
