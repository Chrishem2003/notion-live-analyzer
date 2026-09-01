from __future__ import annotations

from .autonomous import AutonomousController
from .autonomous_models import (
    Action,
    AutonomousResult,
    AutonomousState,
)
from .tool_runner import AutonomousToolRunner


class AutonomousEngine:

    def __init__(
        self,
        runner: AutonomousToolRunner,
        controller: AutonomousController | None = None,
    ):

        self.runner = runner

        self.controller = (
            controller
            or AutonomousController()
        )

    def execute_actions(
        self,
        objective: str,
        actions: list[Action],
    ) -> AutonomousResult:

        state = AutonomousState(
            objective=objective
        )

        for action in actions:

            if not self.controller.can_continue(
                state
            ):
                break

            result = self.runner.run(
                state,
                action,
            )

            self.controller.record(
                state,
                result,
            )

            if not result.success:
                self.controller.fail(
                    state
                )
                break

        else:

            self.controller.complete(
                state
            )

        successful = [
            item
            for item in state.completed_actions
            if item.success
        ]

        if state.status == "completed":

            answer = (
                f"Completed {len(successful)} "
                f"autonomous action(s) successfully."
            )

        else:

            answer = (
                "Autonomous execution stopped "
                "before all requested actions "
                "completed."
            )

        return self.controller.result(
            state,
            answer,
        )
