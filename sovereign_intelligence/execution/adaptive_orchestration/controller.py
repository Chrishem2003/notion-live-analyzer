from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .state import ExecutionState, ExecutionStatus


@dataclass
class ExecutionUpdate:
    """Result of an adaptive execution state update."""

    status: ExecutionStatus
    strategy: str
    progress: float
    confidence: float
    intermediate_score: float
    switched: bool = False
    recovering: bool = False
    terminal: bool = False


class AdaptiveExecutionController:
    """Controls the lifecycle of an adaptive execution session."""

    def __init__(
        self,
        state: ExecutionState,
    ):
        if not isinstance(state, ExecutionState):
            raise TypeError(
                "state must be an ExecutionState instance."
            )

        self.state = state

    @property
    def execution_id(self) -> str:
        return self.state.execution_id

    @property
    def is_terminal(self) -> bool:
        return self.state.is_terminal

    def start(self) -> ExecutionUpdate:
        self.state.start()
        return self._update()

    def update(
        self,
        progress: float,
        *,
        intermediate_score: float | None = None,
        confidence: float | None = None,
        completed_steps: int | None = None,
    ) -> ExecutionUpdate:
        if self.state.is_terminal:
            raise RuntimeError(
                "Cannot update a terminal execution."
            )

        self.state.update_progress(
            progress=progress,
            intermediate_score=intermediate_score,
            confidence=confidence,
            completed_steps=completed_steps,
        )

        return self._update()

    def switch_strategy(
        self,
        strategy: str,
        route: str,
    ) -> ExecutionUpdate:
        if self.state.is_terminal:
            raise RuntimeError(
                "Cannot switch strategy for a terminal execution."
            )

        previous_strategy = self.state.strategy

        self.state.switch_strategy(
            strategy=strategy,
            route=route,
        )

        return self._update(
            switched=(previous_strategy != self.state.strategy)
        )

    def begin_recovery(
        self,
        reason: str,
    ) -> ExecutionUpdate:
        if self.state.is_terminal:
            raise RuntimeError(
                "Cannot recover a terminal execution."
            )

        self.state.begin_recovery(reason)

        return self._update(
            recovering=True
        )

    def resume_after_recovery(self) -> ExecutionUpdate:
        if self.state.status != ExecutionStatus.RECOVERING:
            raise RuntimeError(
                "Execution is not currently recovering."
            )

        self.state.resume_after_recovery()

        return self._update()

    def complete(self) -> ExecutionUpdate:
        if self.state.is_terminal:
            raise RuntimeError(
                "Execution is already terminal."
            )

        self.state.complete()

        return self._update()

    def fail(
        self,
        reason: str,
    ) -> ExecutionUpdate:
        if self.state.is_terminal:
            raise RuntimeError(
                "Execution is already terminal."
            )

        self.state.fail(reason)

        return self._update()

    def cancel(
        self,
        reason: str | None = None,
    ) -> ExecutionUpdate:
        if self.state.is_terminal:
            raise RuntimeError(
                "Execution is already terminal."
            )

        self.state.cancel(reason)

        return self._update()

    def snapshot(self) -> dict[str, Any]:
        return self.state.snapshot()

    def _update(
        self,
        *,
        switched: bool = False,
        recovering: bool = False,
    ) -> ExecutionUpdate:
        return ExecutionUpdate(
            status=self.state.status,
            strategy=self.state.strategy,
            progress=self.state.progress,
            confidence=self.state.confidence,
            intermediate_score=self.state.intermediate_score,
            switched=switched,
            recovering=recovering,
            terminal=self.state.is_terminal,
        )
