from __future__ import annotations

from .adaptive_planner import (
    AdaptivePlanner,
)
from .autonomous import (
    AutonomousController,
)
from .autonomous_models import (
    AutonomousResult,
    AutonomousState,
)
from .tool_runner import (
    AutonomousToolRunner,
)


class AdaptiveExecutionEngine:

    def __init__(
        self,
        runner: AutonomousToolRunner,
        planner: AdaptivePlanner,
        controller: AutonomousController | None = None,
    ):

        self.runner = runner
        self.planner = planner

        self.controller = (
            controller
            or AutonomousController()
        )

    def run(
        self,
        objective: str,
    ) -> AutonomousResult:

        state = AutonomousState(
            objective=objective
        )

        while self.controller.can_continue(
            state
        ):

            decision = self.planner.decide(
                state
            )

            if decision.finished:

                self.controller.complete(
                    state
                )

                break

            if decision.action is None:

                self.controller.complete(
                    state
                )

                break

            result = self.runner.run(
                state,
                decision.action,
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

        if state.status == "completed":

            answer = (
                "Adaptive execution completed "
                f"after {state.iteration} "
                "iteration(s)."
            )

        else:

            answer = (
                "Adaptive execution stopped "
                f"after {state.iteration} "
                "iteration(s)."
            )

        return self.controller.result(
            state,
            answer,
        )
