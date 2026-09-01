from __future__ import annotations

from .ai_action_compiler import (
    AIActionCompiler,
)

from .ai_action_validator import (
    AIActionValidator,
)

from .provider_planner import (
    ProviderPlanningAdapter,
)

from .autonomous_models import (
    AutonomousState,
)

from .tool_runner import (
    AutonomousToolRunner,
)


class ProviderExecutionBridge:

    def __init__(
        self,
        provider,
        runner: AutonomousToolRunner,
        allowed_targets: set[str] | None = None,
    ):

        self.runner = runner

        self.validator = AIActionValidator(
            allowed_actions={"tool"},
            allowed_targets=allowed_targets,
        )

        self.compiler = AIActionCompiler(
            self.validator
        )

        self.planner = ProviderPlanningAdapter(
            provider
        )

    def plan(
        self,
        objective: str,
        available_tools: list[str],
        context: str = "",
    ):

        return self.planner.generate_plan(
            objective=objective,
            available_tools=available_tools,
            context=context,
        )

    def execute_plan(
        self,
        objective: str,
        plan,
    ):

        state = AutonomousState(
            objective=objective
        )

        for proposal in plan.actions:

            action = self.compiler.compile(
                proposal
            )

            result = self.runner.run(
                state,
                action,
            )

            state.completed_actions.append(
                result
            )

            state.iteration += 1

            if not result.success:

                break

        return state
