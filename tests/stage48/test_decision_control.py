from __future__ import annotations

from dataclasses import dataclass

from sovereign_intelligence.execution.control_models import (
    ControlAction,
)
from sovereign_intelligence.execution.decision_control import (
    DecisionControlEngine,
)


@dataclass
class FakeDecision:
    decision: str = "Use strategy A"
    confidence: float = 0.90
    consensus: bool = True
    conflicts: list[str] | None = None

    def __post_init__(self):
        if self.conflicts is None:
            self.conflicts = []


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


def test_high_quality_consensus_finalizes():
    engine = DecisionControlEngine()

    result = engine.decide(
        FakeDecision(),
        FakeEvaluation(),
    )

    assert result.action is ControlAction.FINALIZE
    assert result.retryable is False
    assert result.confidence == 0.9


def test_failed_evaluation_retries():
    engine = DecisionControlEngine()

    result = engine.decide(
        FakeDecision(confidence=0.85),
        FakeEvaluation(
            overall_score=0.50,
            passed=False,
            weaknesses=["Incomplete answer"],
            recommendations=["Improve completeness"],
        ),
    )

    assert result.action is ControlAction.RETRY
    assert result.retryable is True


def test_objective_failure_replans():
    engine = DecisionControlEngine()

    result = engine.decide(
        FakeDecision(confidence=0.80),
        FakeEvaluation(
            overall_score=0.55,
            passed=False,
            weaknesses=["Objective Alignment: weak"],
            recommendations=["Improve objective alignment."],
        ),
    )

    assert result.action is ControlAction.REPLAN
    assert result.retryable is True


def test_conflict_escalates():
    engine = DecisionControlEngine()

    result = engine.decide(
        FakeDecision(
            confidence=0.55,
            consensus=False,
            conflicts=["Conflict between A and B"],
        ),
        FakeEvaluation(
            overall_score=0.70,
            passed=True,
        ),
    )

    assert result.action is ControlAction.ESCALATE
    assert result.retryable is False


def test_retry_limit_rejects():
    engine = DecisionControlEngine(retry_limit=2)

    result = engine.decide(
        FakeDecision(confidence=0.50),
        FakeEvaluation(
            overall_score=0.40,
            passed=False,
        ),
        retry_count=2,
    )

    assert result.action is ControlAction.REJECT
    assert result.retryable is False


def test_missing_decision_rejects():
    engine = DecisionControlEngine()

    result = engine.decide(
        FakeDecision(decision=""),
        FakeEvaluation(),
    )

    assert result.action is ControlAction.REJECT
