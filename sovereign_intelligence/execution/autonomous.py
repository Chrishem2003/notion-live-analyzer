from __future__ import annotations

from .autonomous_models import (
    Action,
    ActionResult,
    AutonomousResult,
    AutonomousState,
)


class AutonomousController:

    def __init__(
        self,
        max_iterations: int = 8,
    ):

        if max_iterations < 1:
            raise ValueError(
                "max_iterations must be at least 1."
            )

        self.max_iterations = max_iterations

    def observe(
        self,
        state: AutonomousState,
        observation: str,
    ):

        if observation.strip():

            state.observations.append(
                observation.strip()
            )

    def record(
        self,
        state: AutonomousState,
        result: ActionResult,
    ):

        state.completed_actions.append(
            result
        )

        if result.success:

            self.observe(
                state,
                str(result.output),
            )

    def can_continue(
        self,
        state: AutonomousState,
    ) -> bool:

        return (
            state.iteration
            < self.max_iterations
            and state.status == "running"
        )

    def complete(
        self,
        state: AutonomousState,
    ):

        state.status = "completed"

    def fail(
        self,
        state: AutonomousState,
    ):

        state.status = "failed"

    def result(
        self,
        state: AutonomousState,
        answer: str,
    ) -> AutonomousResult:

        return AutonomousResult(
            success=(
                state.status
                == "completed"
            ),
            answer=answer,
            iterations=state.iteration,
            actions=list(
                state.completed_actions
            ),
            observations=list(
                state.observations
            ),
        )
