from __future__ import annotations

from .autonomous_models import (
    Action,
    ActionResult,
    AutonomousState,
)
from ..tools.executor import ToolExecutor
from ..tools.specs import ToolRequest


class AutonomousToolRunner:

    def __init__(
        self,
        executor: ToolExecutor,
    ):
        self.executor = executor

    def run(
        self,
        state: AutonomousState,
        action: Action,
    ) -> ActionResult:

        state.iteration += 1

        if action.kind != "tool":
            return ActionResult(
                action=action,
                success=False,
                error=(
                    f"Unsupported action kind: "
                    f"{action.kind}"
                ),
            )

        request = ToolRequest(
            tool=action.target,
            arguments=action.arguments,
        )

        result = self.executor.execute(
            request
        )

        return ActionResult(
            action=action,
            success=result.success,
            output=result.output,
            error=result.error,
        )
