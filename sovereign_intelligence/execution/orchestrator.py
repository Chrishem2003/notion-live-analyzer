from __future__ import annotations

from ..models import (
    AIRequest,
    AIResponse,
    BrainResult,
    Problem,
    Plan,
)

from ..providers.registry import ProviderRegistry
from ..agents.registry import AgentRegistry


class ExecutionEngine:

    def __init__(
        self,
        providers: ProviderRegistry,
        agents: AgentRegistry,
    ):

        self.providers = providers
        self.agents = agents

    def execute(
        self,
        problem: Problem,
        plan: Plan,
        provider_name: str,
        model: str,
        memory_context: str = "",
        evidence_context: str = "",
    ) -> BrainResult:

        provider = self.providers.get(
            provider_name
        )

        trace = []

        instructions = []

        for step in plan.steps:

            agent = self.agents.get(
                step.agent
            )

            instructions.append(
                f"Step: {step.description}\n"
                f"Specialist: {agent.name}\n"
                f"Instructions: "
                f"{agent.instructions()}"
            )

        evidence_section = (
            evidence_context
            if evidence_context.strip()
            else "No repository knowledge was retrieved."
        )

        system = f"""
You are Sovereign Intelligence, the
problem-solving engine of a larger
software platform.

Your job is to solve the user's problem
accurately, not merely produce plausible text.

Operating rules:

1. Understand the objective.
2. Respect constraints.
3. Separate facts from assumptions.
4. Never fabricate tool execution.
5. Never claim certainty without evidence.
6. Use explicit reasoning where useful.
7. Identify uncertainty.
8. Prefer actionable solutions.
9. Preserve existing software functionality.
10. If information is missing, say what is missing.
11. Treat retrieved evidence as supporting context,
    not as unquestionable truth.
12. Do not invent information that is absent
    from the evidence.

Execution plan:

{chr(10).join(instructions)}

Relevant memory:

{memory_context[:12000]}

Retrieved evidence:

{evidence_section}
"""

        request = AIRequest(
            prompt=problem.original,
            system=system,
            model=model,
        )

        trace.append(
            {
                "event": "provider_request",
                "provider": provider_name,
                "model": model,
                "evidence_attached": bool(
                    evidence_context.strip()
                ),
            }
        )

        response: AIResponse = (
            provider.generate(request)
        )

        trace.append(
            {
                "event": "provider_response",
                "provider": response.provider,
                "model": response.model,
                "usage": response.usage,
            }
        )

        return BrainResult(
            answer=response.text,
            plan=plan,
            provider=response.provider,
            model=response.model,
            execution_trace=trace,
        )
