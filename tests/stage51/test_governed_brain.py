from __future__ import annotations

from dataclasses import dataclass

from sovereign_intelligence.models import (
    AIRequest,
    AIResponse,
    BrainResult,
    Plan,
    Problem,
)

from sovereign_intelligence.execution import (
    AgentContribution,
    MultiAgentTeam,
)

from sovereign_intelligence.execution.decision_models import (
    DecisionResult,
)

from sovereign_intelligence.execution.governance import (
    GovernedBrainExecutor,
    GovernedBrainResult,
    GovernedDecisionPipeline,
)

from sovereign_intelligence.verification import (
    VerificationResult,
    Verifier,
)


@dataclass
class FakeProvider:

    name: str = "fake"

    def generate(
        self,
        request: AIRequest,
    ) -> AIResponse:

        agent = "specialist"

        if "Agent identity:" in request.prompt:
            agent = (
                request.prompt
                .split(
                    "Agent identity:",
                    1,
                )[1]
                .splitlines()[0]
                .strip()
            )

        return AIResponse(
            text=(
                "Conclusion: The governed architecture "
                "is supported by the "
                f"{agent} specialist."
            ),
            provider=self.name,
            model=request.model or "fake-model",
        )


class FakeProviders:

    def __init__(self):
        self.provider = FakeProvider()

    def get(self, name: str):

        assert name == self.provider.name

        return self.provider


def make_plan():

    return Plan(
        objective="Test governed execution",
        steps=[],
    )


def make_problem():

    return Problem(
        original=(
            "Explain how the governed architecture works."
        ),
        objective=(
            "Explain how the governed architecture works."
        ),
    )


def make_executor():

    return GovernedBrainExecutor(
        providers=FakeProviders(),
    )


def test_stage51_executor_returns_governed_result():

    result = make_executor().execute(
        problem=make_problem(),
        plan=make_plan(),
        provider_name="fake",
        model="fake-model",
    )

    assert isinstance(
        result,
        GovernedBrainResult,
    )

    assert isinstance(
        result.brain_result,
        BrainResult,
    )

    assert isinstance(
        result.team_result.contributions,
        list,
    )

    assert isinstance(
        result.decision,
        DecisionResult,
    )

    assert result.governed_decision.decision_id


def test_stage51_real_agent_contributions_exist():

    result = make_executor().execute(
        problem=make_problem(),
        plan=make_plan(),
        provider_name="fake",
        model="fake-model",
    )

    assert result.team_result.successful_agents > 0

    for contribution in (
        result.team_result.contributions
    ):

        assert isinstance(
            contribution,
            AgentContribution,
        )

        assert contribution.success

        assert contribution.answer.strip()


def test_stage51_decision_engine_produces_decision():

    result = make_executor().execute(
        problem=make_problem(),
        plan=make_plan(),
        provider_name="fake",
        model="fake-model",
    )

    assert isinstance(
        result.decision,
        DecisionResult,
    )

    assert result.decision.votes

    assert (
        result.decision.metadata["specialists"]
        == len(result.decision.votes)
    )


def test_stage51_verifier_is_real():

    result = make_executor().execute(
        problem=make_problem(),
        plan=make_plan(),
        provider_name="fake",
        model="fake-model",
    )

    assert isinstance(
        result.verification,
        VerificationResult,
    )

    expected = Verifier().evaluate(
        result.answer,
    )

    assert (
        result.verification.passed
        == expected.passed
    )

    assert (
        result.verification.confidence
        == expected.confidence
    )

    assert (
        result.verification.issues
        == expected.issues
    )


def test_stage51_governance_pipeline_runs():

    result = make_executor().execute(
        problem=make_problem(),
        plan=make_plan(),
        provider_name="fake",
        model="fake-model",
    )

    assert (
        result.control
        is result.governed_decision.control
    )

    assert (
        result.record
        is result.governed_decision.record
    )

    assert (
        result.assessment
        is result.governed_decision.assessment
    )


def test_stage51_verification_confidence_reaches_governance():

    result = make_executor().execute(
        problem=make_problem(),
        plan=make_plan(),
        provider_name="fake",
        model="fake-model",
    )

    assert (
        result.record.evaluation_score
        == result.verification.confidence
    )


def test_stage51_execution_trace_contains_full_governance_chain():

    result = make_executor().execute(
        problem=make_problem(),
        plan=make_plan(),
        provider_name="fake",
        model="fake-model",
    )

    events = [
        item["event"]
        for item in result.execution_trace
    ]

    assert (
        "governed_multi_agent_started"
        in events
    )

    assert (
        "multi_agent_completed"
        in events
    )

    assert (
        "decision_engine_completed"
        in events
    )

    assert (
        "verification_completed"
        in events
    )

    assert (
        "governance_completed"
        in events
    )


def test_stage51_team_confidence_is_bounded():

    result = make_executor().execute(
        problem=make_problem(),
        plan=make_plan(),
        provider_name="fake",
        model="fake-model",
    )

    assert (
        0.0
        <= result.team_result.confidence
        <= 1.0
    )


def test_stage51_explicit_decision_id_is_preserved():

    result = make_executor().execute(
        problem=make_problem(),
        plan=make_plan(),
        provider_name="fake",
        model="fake-model",
        decision_id="stage51-test-id",
    )

    assert (
        result.governed_decision.decision_id
        == "stage51-test-id"
    )


def test_stage51_governance_pipeline_is_injectable():

    pipeline = GovernedDecisionPipeline()

    executor = GovernedBrainExecutor(
        providers=FakeProviders(),
        governance_pipeline=pipeline,
    )

    result = executor.execute(
        problem=make_problem(),
        plan=make_plan(),
        provider_name="fake",
        model="fake-model",
    )

    assert result.governed_decision is not None


def test_stage51_invalid_problem_rejected():

    executor = make_executor()

    try:

        executor.execute(
            problem="not a Problem",
            plan=make_plan(),
            provider_name="fake",
            model="fake-model",
        )

    except TypeError:

        return

    raise AssertionError(
        "Expected TypeError"
    )


def test_stage51_invalid_plan_rejected():

    executor = make_executor()

    try:

        executor.execute(
            problem=make_problem(),
            plan="not a Plan",
            provider_name="fake",
            model="fake-model",
        )

    except TypeError:

        return

    raise AssertionError(
        "Expected TypeError"
    )


def test_stage51_empty_prompt_rejected_by_brain():

    from sovereign_intelligence.orchestrator import (
        SovereignBrain,
    )

    brain = SovereignBrain()

    try:

        brain.solve_governed("")

    except ValueError:

        return

    raise AssertionError(
        "Expected ValueError"
    )


def test_stage51_existing_solve_remains_available():

    from sovereign_intelligence.orchestrator import (
        SovereignBrain,
    )

    assert hasattr(
        SovereignBrain,
        "solve",
    )

    assert callable(
        SovereignBrain.solve,
    )


def test_stage51_governed_solve_remains_separate():

    from sovereign_intelligence.orchestrator import (
        SovereignBrain,
    )

    assert hasattr(
        SovereignBrain,
        "solve_governed",
    )

    assert callable(
        SovereignBrain.solve_governed,
    )
