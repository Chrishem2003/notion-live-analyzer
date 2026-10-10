import pytest

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle import (
    build_retention_registry_review_lifecycle,
    evaluate_retention_registry_review_lifecycle,
    validate_retention_registry_lifecycle,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_reconciliation import (
    reconcile_retention_registry_reviews,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_review import (
    review_retention_registry,
)


def _monitor(state="RETENTION_REGISTRY_HEALTHY"):
    recommendation = {
        "RETENTION_REGISTRY_HEALTHY": "NO_RETENTION_REGISTRY_ACTION",
        "NO_HISTORY": "REVIEW_RETENTION_REGISTRY",
        "CONTROL_REQUIRED": "PRESERVE_AND_ESCALATE",
    }[state]
    payload = {
        "policy_version": "phase125-v1",
        "observed_at": "2026-10-04T12:00:00+00:00",
        "registry_policy_version": "phase124-v1",
        "state": state,
        "snapshot_count": 1 if state != "NO_HISTORY" else 0,
        "valid_snapshot_count": 1 if state != "NO_HISTORY" else 0,
        "expected_count": 1 if state != "NO_HISTORY" else 0,
        "history_state": "HISTORY_READY" if state != "NO_HISTORY" else "NO_HISTORY",
        "history_reconciliation_fingerprint": "synthetic-history",
        "findings": [],
        "retention_registry_recommendation": recommendation,
        "read_only": True,
        "human_governed": True,
        "automatic_repair_performed": False,
        "execution_gate_closed": True,
        "execution_permitted": False,
        "execution_performed": False,
        "interpretation": "RETENTION_AUTHORIZATION_REGISTRY_INTEGRITY_MONITORING",
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
        "emergency_action": None,
    }
    return dict(payload, monitor_fingerprint=fingerprint(payload))


def _review(outcome="ACKNOWLEDGED", state="RETENTION_REGISTRY_HEALTHY"):
    return review_retention_registry(
        _monitor(state),
        actor_id="reviewer",
        role="coordinator",
        outcome=outcome,
        reviewed_at="2026-10-04T12:01:00+00:00",
    )


def _reconciliation(review, state="RETENTION_REGISTRY_HEALTHY"):
    return reconcile_retention_registry_reviews(
        [_monitor(state)], [review], expected_review_count=1
    )


def test_acknowledged_maps_to_acknowledged():
    lifecycle = evaluate_retention_registry_review_lifecycle(
        _review(), evaluated_at="2026-10-04T12:02:00+00:00"
    )
    assert lifecycle["lifecycle_state"] == "ACKNOWLEDGED"
    assert lifecycle["decision_executed"] is False
    assert lifecycle["execution_gate_closed"] is True
    assert lifecycle["execution_permitted"] is False
    assert lifecycle["execution_performed"] is False
    assert validate_retention_registry_lifecycle(lifecycle)["lifecycle_fingerprint"] == lifecycle["lifecycle_fingerprint"]


def test_review_retention_registry_maps_to_deferred():
    review = _review("REVIEW_RETENTION_REGISTRY", "NO_HISTORY")
    lifecycle = evaluate_retention_registry_review_lifecycle(
        review, evaluated_at="2026-10-04T12:02:00+00:00"
    )
    assert lifecycle["lifecycle_state"] == "DEFERRED"


def test_preserve_and_escalate_maps_to_escalated():
    review = _review("PRESERVE_AND_ESCALATE", "CONTROL_REQUIRED")
    lifecycle = evaluate_retention_registry_review_lifecycle(
        review, evaluated_at="2026-10-04T12:02:00+00:00"
    )
    assert lifecycle["lifecycle_state"] == "ESCALATED"


def test_escalated_maps_to_escalated():
    review = _review("ESCALATED", "CONTROL_REQUIRED")
    lifecycle = evaluate_retention_registry_review_lifecycle(
        review, evaluated_at="2026-10-04T12:02:00+00:00"
    )
    assert lifecycle["lifecycle_state"] == "ESCALATED"


def test_build_bundle_from_reconciled_reviews():
    review = _review()
    reconciliation = _reconciliation(review)
    assert reconciliation["state"] == "RECONCILED"
    bundle = build_retention_registry_review_lifecycle(
        reconciliation, [review], evaluated_at="2026-10-04T12:02:00+00:00"
    )
    assert bundle["lifecycle_count"] == 1
    assert bundle["reconciliation_fingerprint"] == reconciliation["reconciliation_fingerprint"]
    assert bundle["lifecycles"][0]["monitor_fingerprint"] == review["monitor_fingerprint"]


def test_non_reconciled_blocked():
    review = _review()
    bad = reconcile_retention_registry_reviews(
        [_monitor()], [], expected_review_count=0
    )
    assert bad["state"] == "CONTROL_REQUIRED"
    with pytest.raises(ValueError, match="RECONCILIATION_MUST_BE_RECONCILED"):
        build_retention_registry_review_lifecycle(
            bad, [review], evaluated_at="2026-10-04T12:02:00+00:00"
        )


def test_tampered_lifecycle_rejected():
    lifecycle = evaluate_retention_registry_review_lifecycle(
        _review(), evaluated_at="2026-10-04T12:02:00+00:00"
    )
    lifecycle["lifecycle_state"] = "ESCALATED"
    with pytest.raises(ValueError, match="LIFECYCLE_STATE_OUTCOME_MISMATCH"):
        validate_retention_registry_lifecycle(lifecycle)


def test_deterministic_fingerprint():
    review = _review()
    first = evaluate_retention_registry_review_lifecycle(
        review, evaluated_at="2026-10-04T12:02:00+00:00"
    )
    second = evaluate_retention_registry_review_lifecycle(
        review, evaluated_at="2026-10-04T12:02:00+00:00"
    )
    assert first == second


def test_execution_boundary_tamper_rejected():
    lifecycle = evaluate_retention_registry_review_lifecycle(
        _review(), evaluated_at="2026-10-04T12:02:00+00:00"
    )
    lifecycle["execution_performed"] = True
    with pytest.raises(ValueError, match="INVALID_EXECUTION_CONTROLS"):
        validate_retention_registry_lifecycle(lifecycle)
