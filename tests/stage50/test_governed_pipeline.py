from __future__ import annotations

from dataclasses import dataclass

import pytest

from sovereign_intelligence.execution.control_models import (
    ControlAction,
)
from sovereign_intelligence.execution.decision_models import (
    DecisionResult,
)
from sovereign_intelligence.execution.governance import (
    DecisionGovernanceEngine,
    DecisionHistory,
    GovernedDecision,
    GovernedDecisionPipeline,
)


@dataclass
class FakeEvaluation:
    overall_score: float = 0.90
    passed: bool = True
    weaknesses: list[str] | None = None
    recommendations: list[str] | None = None

    def __post_init__(self):
        if self.weaknesses is None:
            self.weaknesses = []

        if self.recommendations is None:
            self.recommendations = []


def make_decision(
    *,
    decision: str = "Use strategy A",
    confidence: float = 0.90,
    consensus: bool = True,
    conflicts: list[str] | None = None,
) -> DecisionResult:

    return DecisionResult(
        decision=decision,
        confidence=confidence,
        consensus=consensus,
        conflicts=conflicts or [],
        rationale="test rationale",
    )


def test_successful_pipeline_finalizes():

    pipeline = GovernedDecisionPipeline()

    decision = make_decision()

    result = pipeline.run(
        decision,
        FakeEvaluation(),
        decision_id="decision-1",
    )

    assert isinstance(
        result,
        GovernedDecision,
    )

    assert result.control.action is (
        ControlAction.FINALIZE
    )

    assert result.record.action is (
        ControlAction.FINALIZE
    )

    assert result.assessment.accepted is True


def test_failed_evaluation_retries():

    pipeline = GovernedDecisionPipeline()

    decision = make_decision(
        confidence=0.85,
    )

    evaluation = FakeEvaluation(
        overall_score=0.50,
        passed=False,
        weaknesses=["Incomplete answer"],
        recommendations=["Improve completeness"],
    )

    result = pipeline.run(
        decision,
        evaluation,
        decision_id="decision-1",
    )

    assert result.control.action is (
        ControlAction.RETRY
    )

    assert result.control.retryable is True


def test_objective_failure_replans():

    pipeline = GovernedDecisionPipeline()

    decision = make_decision(
        confidence=0.80,
    )

    evaluation = FakeEvaluation(
        overall_score=0.55,
        passed=False,
        weaknesses=[
            "Objective Alignment: weak"
        ],
        recommendations=[
            "Improve objective alignment."
        ],
    )

    result = pipeline.run(
        decision,
        evaluation,
        decision_id="decision-1",
    )

    assert result.control.action is (
        ControlAction.REPLAN
    )


def test_conflict_escalates():

    pipeline = GovernedDecisionPipeline()

    decision = make_decision(
        confidence=0.55,
        consensus=False,
        conflicts=[
            "Conflict between A and B"
        ],
    )

    result = pipeline.run(
        decision,
        FakeEvaluation(
            overall_score=0.70,
            passed=True,
        ),
        decision_id="decision-1",
    )

    assert result.control.action is (
        ControlAction.ESCALATE
    )

    assert result.assessment.escalation_detected is True


def test_retry_limit_rejects():

    pipeline = GovernedDecisionPipeline()

    decision = make_decision(
        confidence=0.50,
        consensus=False,
    )

    evaluation = FakeEvaluation(
        overall_score=0.40,
        passed=False,
    )

    result = pipeline.run(
        decision,
        evaluation,
        decision_id="decision-1",
        retry_count=2,
    )

    assert result.control.action is (
        ControlAction.REJECT
    )

    assert result.control.retryable is False


def test_history_is_preserved():

    history = DecisionHistory()

    governance = DecisionGovernanceEngine(
        history=history
    )

    pipeline = GovernedDecisionPipeline(
        governance_engine=governance
    )

    first = pipeline.run(
        make_decision(),
        FakeEvaluation(),
        decision_id="decision-1",
    )

    second = pipeline.run(
        make_decision(
            decision="Use strategy B",
            confidence=0.80,
        ),
        FakeEvaluation(
            overall_score=0.80,
        ),
        decision_id="decision-2",
    )

    assert first.record.decision_id == (
        "decision-1"
    )

    assert second.record.decision_id == (
        "decision-2"
    )

    assert history.count() == 2


def test_original_decision_is_preserved():

    decision = make_decision(
        confidence=0.91,
        consensus=True,
    )

    original = (
        decision.decision,
        decision.confidence,
        decision.consensus,
        list(decision.conflicts),
    )

    pipeline = GovernedDecisionPipeline()

    result = pipeline.run(
        decision,
        FakeEvaluation(),
        decision_id="decision-1",
    )

    assert result.decision is decision

    assert (
        decision.decision,
        decision.confidence,
        decision.consensus,
        list(decision.conflicts),
    ) == original


def test_invalid_decision_type_rejected():

    pipeline = GovernedDecisionPipeline()

    with pytest.raises(TypeError):
        pipeline.run(
            "not a decision",
            FakeEvaluation(),
            decision_id="decision-1",
        )


def test_empty_decision_id_rejected():

    pipeline = GovernedDecisionPipeline()

    with pytest.raises(ValueError):
        pipeline.run(
            make_decision(),
            FakeEvaluation(),
            decision_id="",
        )


def test_negative_retry_count_rejected():

    pipeline = GovernedDecisionPipeline()

    with pytest.raises(ValueError):
        pipeline.run(
            make_decision(),
            FakeEvaluation(),
            decision_id="decision-1",
            retry_count=-1,
        )


def test_explicit_governance_values_are_used():

    pipeline = GovernedDecisionPipeline()

    result = pipeline.run(
        make_decision(
            confidence=0.80,
            consensus=False,
        ),
        FakeEvaluation(
            overall_score=0.50,
            passed=False,
        ),
        decision_id="decision-1",
        decision_confidence=0.95,
        evaluation_score=0.95,
        consensus=True,
    )

    assert result.record.decision_confidence == 0.95
    assert result.record.evaluation_score == 0.95
    assert result.record.consensus is True


def test_stage47_style_evaluation_without_score_is_supported():

    pipeline = GovernedDecisionPipeline()

    class Stage47LikeEvaluation:
        pass

    result = pipeline.run(
        make_decision(
            confidence=0.80,
            consensus=False,
        ),
        Stage47LikeEvaluation(),
        decision_id="decision-1",
    )

    assert result.record.evaluation_score == 0.0


def test_repeated_execution_is_deterministic():

    pipeline = GovernedDecisionPipeline()

    decision = make_decision(
        confidence=0.90,
        consensus=True,
    )

    evaluation = FakeEvaluation(
        overall_score=0.90,
        passed=True,
    )

    first = pipeline.run(
        decision,
        evaluation,
        decision_id="decision-1",
    )

    second = pipeline.run(
        decision,
        evaluation,
        decision_id="decision-2",
    )

    assert first.control.action is (
        second.control.action
    )

    assert first.control.confidence == (
        second.control.confidence
    )


def test_governance_history_is_ordered():

    history = DecisionHistory()

    pipeline = GovernedDecisionPipeline(
        governance_engine=DecisionGovernanceEngine(
            history=history
        )
    )

    pipeline.run(
        make_decision(
            confidence=0.90
        ),
        FakeEvaluation(),
        decision_id="one",
    )

    pipeline.run(
        make_decision(
            confidence=0.80
        ),
        FakeEvaluation(
            overall_score=0.80
        ),
        decision_id="two",
    )

    assert history.actions() == (
        "finalize",
        "finalize",
    )
