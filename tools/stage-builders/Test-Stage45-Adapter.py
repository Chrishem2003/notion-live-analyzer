from sovereign_intelligence.integration.adaptive_brain import (
    AdaptiveBrainExecutionAdapter,
)
from sovereign_intelligence.execution.orchestrator import ExecutionEngine
from sovereign_intelligence.models import (
    AIResponse,
    Problem,
    Plan,
)
from dataclasses import dataclass


class FakeProvider:
    def generate(self, request):
        return AIResponse(
            text=(
                "The objective has been analyzed successfully. "
                "The requested solution is actionable and supported "
                "by the available context."
            ),
            provider="fake",
            model=request.model,
            usage={},
        )


class FakeProviders:
    def get(self, name):
        return FakeProvider()


@dataclass
class FakeAgent:
    name: str = "Test Specialist"

    def instructions(self):
        return "Analyze the task carefully."


class FakeAgents:
    def get(self, name):
        return FakeAgent()


@dataclass
class FakeStep:
    description: str = "Analyze the objective"
    agent: str = "test"


providers = FakeProviders()
agents = FakeAgents()

executor = ExecutionEngine(
    providers=providers,
    agents=agents,
)

adapter = AdaptiveBrainExecutionAdapter(
    executor=executor,
)

problem = Problem(
    original="Analyze this software architecture and provide a solution.",
    objective="Analyze this software architecture and provide a solution.",
)

plan = Plan(
    objective="Analyze this software architecture and provide a solution.",
    steps=[
        FakeStep(),
    ],
)

result = adapter.execute(
    problem=problem,
    plan=plan,
    provider_name="fake",
    model="test-model",
    memory_context="",
    evidence_context="",
)

print("ANSWER_OK=", bool(result.result.answer))
print("STRATEGY=", result.state.strategy)
print("ROUTE=", result.state.route)
print("STATUS=", result.state.status.value)
print("PROGRESS=", result.state.progress)
print("TRACE_COUNT=", len(result.trace))
print(
    "TRACE_NAMES=",
    [event["name"] for event in result.trace],
)

if not result.result.answer:
    raise SystemExit("FAIL: Empty answer.")

if result.state.is_terminal is not True:
    raise SystemExit("FAIL: Execution did not reach terminal state.")

if result.state.status.value != "completed":
    raise SystemExit(
        f"FAIL: Unexpected status: {result.state.status.value}"
    )

if result.state.progress < 0.80:
    raise SystemExit(
        f"FAIL: Unexpected progress: {result.state.progress}"
    )

print("STAGE45_ADAPTER_EXECUTION_OK")
