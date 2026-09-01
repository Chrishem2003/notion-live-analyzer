from __future__ import annotations

from .context import ProblemContext


class ProblemSolver:

    def __init__(
        self,
        tool_reasoner=None,
        planner=None,
        verifier=None,
    ):

        self.tool_reasoner = tool_reasoner
        self.planner = planner
        self.verifier = verifier

    def create_context(
        self,
        problem: str,
    ):

        return ProblemContext(
            problem=problem
        )

    def discover_capabilities(
        self,
        context: ProblemContext,
    ):

        if self.tool_reasoner is None:
            return []

        capabilities = (
            self.tool_reasoner.discover(
                context.problem
            )
        )

        context.metadata[
            "capabilities"
        ] = capabilities

        return capabilities

    def create_plan(
        self,
        context: ProblemContext,
    ):

        if self.planner is None:
            return []

        plan = self.planner.plan(
            context.problem
        )

        context.plan.extend(plan)

        return plan

    def observe(
        self,
        context: ProblemContext,
        observation,
    ):

        context.add_observation(
            observation
        )

        return observation

    def record_tool_result(
        self,
        context: ProblemContext,
        result,
    ):

        context.add_tool_result(
            result
        )

        return result

    def record_verification(
        self,
        context: ProblemContext,
        result,
    ):

        context.add_verification(
            result
        )

        return result

    def state(
        self,
        context: ProblemContext,
    ):

        return context.snapshot()
