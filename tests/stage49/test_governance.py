from __future__ import annotations

from sovereign_intelligence.execution.control_models import (
    ControlAction,
    ControlDecision,
)
from sovereign_intelligence.execution.governance import (
    DecisionGovernanceEngine,
    DecisionHistory,
)


def make_control(
    action: ControlAction = ControlAction.FINALIZE,
    confidence: float = 0.90,
) -> ControlDecision:
    return ControlDecision(
        action=action,
        reason="test decision",
        confidence=confidence,
        retryable=action in {
            ControlAction.RETRY,
            ControlAction.REPLAN,
        },
        metadata={"source": "stage49-test"},
    )


def test_first_record_is_accepted():
    engine = DecisionGovernanceEngine()

    record = engine.record(
        make_control(),
        decision_id="decision-1",
        decision_confidence=0.90,
        evaluation_score=0.90,
        consensus=True,
    )

    assessment = engine.assess(record)

    assert record.action is ControlAction.FINALIZE
    assert assessment.accepted is True
    assert assessment.consistency_score == 1.0


def test_history_preserves_order():
    history = DecisionHistory()
    engine = DecisionGovernanceEngine(history)

    engine.record(
        make_control(ControlAction.RETRY, 0.50),
        decision_id="decision-1",
    )

    engine.record(
        make_control(ControlAction.REPLAN, 0.60),
        decision_id="decision-2",
    )

    assert history.count() == 2
    assert history.actions() == (
        "retry",
        "replan",
    )


def test_repeated_action_is_detected():
    engine = DecisionGovernanceEngine()

    first = engine.record(
        make_control(ControlAction.RETRY, 0.60),
        decision_id="decision-1",
    )

    engine.record(
        make_control(ControlAction.RETRY, 0.62),
        decision_id="decision-2",
    )

    assessment = engine.assess(first)

    assert assessment.repeated_action is True


def test_escalation_is_detected():
    engine = DecisionGovernanceEngine()

    engine.record(
        make_control(ControlAction.ESCALATE, 0.40),
        decision_id="decision-1",
    )

    latest = engine.record(
        make_control(ControlAction.RETRY, 0.50),
        decision_id="decision-2",
    )

    assessment = engine.assess(latest)

    assert assessment.escalation_detected is True


def test_confidence_stability_is_bounded():
    engine = DecisionGovernanceEngine()

    engine.record(
        make_control(ControlAction.FINALIZE, 0.90),
        decision_id="decision-1",
    )

    latest = engine.record(
        make_control(ControlAction.FINALIZE, 0.80),
        decision_id="decision-2",
    )

    assessment = engine.assess(latest)

    assert 0.0 <= assessment.confidence_stability <= 1.0


def test_empty_history_is_not_accepted():
    engine = DecisionGovernanceEngine()

    assessment = engine.assess()

    assert assessment.accepted is False
    assert assessment.consistency_score == 0.0


def test_invalid_decision_id_rejected():
    engine = DecisionGovernanceEngine()

    try:
        engine.record(
            make_control(),
            decision_id="",
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError for empty decision_id"
        )


def test_control_decision_is_not_modified():
    control = make_control(
        ControlAction.FINALIZE,
        0.91,
    )

    engine = DecisionGovernanceEngine()

    engine.record(
        control,
        decision_id="decision-1",
    )

    assert control.action is ControlAction.FINALIZE
    assert control.confidence == 0.91
    assert control.retryable is False
