from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .state import ExecutionState, ExecutionStatus


@dataclass
class ProgressAssessment:
    """Assessment of the current execution health."""

    healthy: bool
    needs_reassessment: bool
    progress: float
    intermediate_score: float
    confidence: float
    status: ExecutionStatus

    reason: str

    stagnant: bool = False
    score_below_threshold: bool = False
    confidence_below_threshold: bool = False

    metadata: dict[str, Any] = field(default_factory=dict)


class ExecutionProgressMonitor:
    """Observes execution progress and identifies unhealthy execution."""

    def __init__(
        self,
        *,
        minimum_score: float = 0.40,
        minimum_confidence: float = 0.40,
        minimum_progress_delta: float = 0.01,
    ):
        for name, value in {
            "minimum_score": minimum_score,
            "minimum_confidence": minimum_confidence,
            "minimum_progress_delta": minimum_progress_delta,
        }.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1."
                )

        self.minimum_score = minimum_score
        self.minimum_confidence = minimum_confidence
        self.minimum_progress_delta = minimum_progress_delta

        self._last_progress: dict[str, float] = {}

    def assess(
        self,
        state: ExecutionState,
    ) -> ProgressAssessment:
        if not isinstance(state, ExecutionState):
            raise TypeError(
                "state must be an ExecutionState instance."
            )

        execution_id = state.execution_id

        previous_progress = self._last_progress.get(
            execution_id
        )

        stagnant = (
            previous_progress is not None
            and (
                state.progress - previous_progress
                < self.minimum_progress_delta
            )
        )

        self._last_progress[execution_id] = state.progress

        score_below_threshold = (
            state.intermediate_score < self.minimum_score
        )

        confidence_below_threshold = (
            state.confidence < self.minimum_confidence
        )

        terminal = state.status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        }

        unhealthy_signals = []

        if score_below_threshold:
            unhealthy_signals.append(
                "intermediate score below threshold"
            )

        if confidence_below_threshold:
            unhealthy_signals.append(
                "confidence below threshold"
            )

        if stagnant:
            unhealthy_signals.append(
                "execution progress is stagnant"
            )

        healthy = (
            not unhealthy_signals
            and state.status
            not in {
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELLED,
            }
        )

        needs_reassessment = (
            not terminal
            and not healthy
        )

        if healthy:
            reason = (
                "Execution is progressing within the configured "
                "health thresholds."
            )
        elif terminal:
            reason = (
                "Execution is terminal; no further reassessment "
                "is required."
            )
        else:
            reason = (
                "Execution requires reassessment: "
                + ", ".join(unhealthy_signals)
                + "."
            )

        return ProgressAssessment(
            healthy=healthy,
            needs_reassessment=needs_reassessment,
            progress=state.progress,
            intermediate_score=state.intermediate_score,
            confidence=state.confidence,
            status=state.status,
            reason=reason,
            stagnant=stagnant,
            score_below_threshold=score_below_threshold,
            confidence_below_threshold=confidence_below_threshold,
            metadata={
                "execution_id": execution_id,
                "previous_progress": previous_progress,
                "minimum_score": self.minimum_score,
                "minimum_confidence": self.minimum_confidence,
                "minimum_progress_delta": self.minimum_progress_delta,
            },
        )

    def reset(self, execution_id: str) -> None:
        execution_id = execution_id.strip()

        if not execution_id:
            raise ValueError(
                "execution_id cannot be empty."
            )

        self._last_progress.pop(
            execution_id,
            None,
        )

    def tracked_executions(self) -> int:
        return len(self._last_progress)
