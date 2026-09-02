from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class ExecutionStatus(str, Enum):
    CREATED = "created"
    STARTED = "started"
    RUNNING = "running"
    SWITCHING = "switching"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionState:
    """Mutable state for one adaptive execution session."""

    execution_id: str = field(
        default_factory=lambda: uuid4().hex
    )

    strategy: str = "direct"
    route: str = "standard_execution"
    problem_type: str = "general"

    status: ExecutionStatus = ExecutionStatus.CREATED

    progress: float = 0.0

    attempt: int = 0
    completed_steps: int = 0
    total_steps: int = 0

    intermediate_score: float = 0.0
    confidence: float = 0.0

    started_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None

    failure_reason: str | None = None

    strategy_history: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.strategy = self.strategy.strip().lower()

        if not self.strategy:
            raise ValueError("strategy cannot be empty.")

        self.route = self.route.strip().lower()

        if not self.route:
            raise ValueError("route cannot be empty.")

        self.problem_type = self.problem_type.strip().lower()

        if not self.problem_type:
            raise ValueError("problem_type cannot be empty.")

        self._validate_numeric_state()

        if not self.strategy_history:
            self.strategy_history.append(self.strategy)

    def _validate_numeric_state(self) -> None:
        for name, value in {
            "progress": self.progress,
            "intermediate_score": self.intermediate_score,
            "confidence": self.confidence,
        }.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1."
                )

        if self.attempt < 0:
            raise ValueError("attempt cannot be negative.")

        if self.completed_steps < 0:
            raise ValueError(
                "completed_steps cannot be negative."
            )

        if self.total_steps < 0:
            raise ValueError(
                "total_steps cannot be negative."
            )

        if self.total_steps and self.completed_steps > self.total_steps:
            raise ValueError(
                "completed_steps cannot exceed total_steps."
            )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    def start(self) -> None:
        if self.status not in {
            ExecutionStatus.CREATED,
            ExecutionStatus.STARTED,
        }:
            raise ValueError(
                f"Cannot start execution from status '{self.status.value}'."
            )

        timestamp = self._timestamp()

        if self.started_at is None:
            self.started_at = timestamp

        self.updated_at = timestamp
        self.status = ExecutionStatus.RUNNING

    def update_progress(
        self,
        progress: float,
        *,
        intermediate_score: float | None = None,
        confidence: float | None = None,
        completed_steps: int | None = None,
    ) -> None:
        if not 0.0 <= progress <= 1.0:
            raise ValueError(
                "progress must be between 0 and 1."
            )

        if intermediate_score is not None:
            if not 0.0 <= intermediate_score <= 1.0:
                raise ValueError(
                    "intermediate_score must be between 0 and 1."
                )
            self.intermediate_score = intermediate_score

        if confidence is not None:
            if not 0.0 <= confidence <= 1.0:
                raise ValueError(
                    "confidence must be between 0 and 1."
                )

            self.confidence = confidence

        if completed_steps is not None:
            if completed_steps < 0:
                raise ValueError(
                    "completed_steps cannot be negative."
                )

            if (
                self.total_steps
                and completed_steps > self.total_steps
            ):
                raise ValueError(
                    "completed_steps cannot exceed total_steps."
                )

            self.completed_steps = completed_steps

        self.progress = progress
        self.updated_at = self._timestamp()

    def switch_strategy(
        self,
        strategy: str,
        route: str,
    ) -> None:
        strategy = strategy.strip().lower()
        route = route.strip().lower()

        if not strategy:
            raise ValueError("strategy cannot be empty.")

        if not route:
            raise ValueError("route cannot be empty.")

        self.status = ExecutionStatus.SWITCHING
        self.strategy = strategy
        self.route = route

        self.strategy_history.append(strategy)
        self.updated_at = self._timestamp()

        self.status = ExecutionStatus.RUNNING

    def begin_recovery(self, reason: str) -> None:
        reason = reason.strip()

        if not reason:
            raise ValueError("Recovery reason cannot be empty.")

        self.failure_reason = reason
        self.status = ExecutionStatus.RECOVERING
        self.attempt += 1
        self.updated_at = self._timestamp()

    def resume_after_recovery(self) -> None:
        """Resume execution after a recovery attempt."""

        if self.status != ExecutionStatus.RECOVERING:
            raise ValueError(
                "Execution must be in recovering status before resuming."
            )

        self.status = ExecutionStatus.RUNNING
        self.updated_at = self._timestamp()

    def complete(self) -> None:
        timestamp = self._timestamp()

        self.progress = 1.0
        self.status = ExecutionStatus.COMPLETED
        self.updated_at = timestamp
        self.completed_at = timestamp

    def fail(self, reason: str) -> None:
        reason = reason.strip()

        if not reason:
            raise ValueError("Failure reason cannot be empty.")

        timestamp = self._timestamp()

        self.failure_reason = reason
        self.status = ExecutionStatus.FAILED
        self.updated_at = timestamp
        self.completed_at = timestamp

    def cancel(self, reason: str | None = None) -> None:
        timestamp = self._timestamp()

        if reason:
            self.failure_reason = reason.strip()

        self.status = ExecutionStatus.CANCELLED
        self.updated_at = timestamp
        self.completed_at = timestamp

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        }

    @property
    def strategy_switch_count(self) -> int:
        return max(0, len(self.strategy_history) - 1)

    def snapshot(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "strategy": self.strategy,
            "route": self.route,
            "problem_type": self.problem_type,
            "status": self.status.value,
            "progress": self.progress,
            "attempt": self.attempt,
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps,
            "intermediate_score": self.intermediate_score,
            "confidence": self.confidence,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "failure_reason": self.failure_reason,
            "strategy_history": list(self.strategy_history),
            "strategy_switch_count": self.strategy_switch_count,
            "metadata": dict(self.metadata),
        }

