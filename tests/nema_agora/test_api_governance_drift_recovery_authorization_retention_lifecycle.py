import pytest

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_lifecycle import (
    build_retention_review_lifecycle,
    evaluate_retention_review_lifecycle,
    validate_retention_lifecycle,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_reconciliation import (
    reconcile_retention_reviews,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_review import review_retention_health


def _monitor():
    payload = {
        "policy_version": "phase117-v1", "observed_at": "2026-10-04T12:00:00+00:00",
        "registry_policy_version": "phase116-v1", "state": "RETENTION_HEALTHY",
        "snapshot_count": 1, "valid_snapshot_count": 1, "expected_count": 1,
        "history_state": "HISTORY_READY", "history_reconciliation_fingerprint": "synthetic-history",
        "findings": [], "retention_recommendation": "NO_RETENTION_ACTION",
        "read_only": True, "automatic_repair_performed": False, "execution_gate_closed": True,
        "interpretation": "AUTHORIZATION_RETENTION_INTEGRITY_MONITORING",
        "environmental_conclusion": None, "regulatory_conclusion": None, "enforcement_action": None,
    }
    return dict(payload, monitor_fingerprint=fingerprint(payload))


def _review(outcome="ACKNOWLEDGED"):
    return review_retention_health(
        _monitor(), actor_id="reviewer", role="coordinator", outcome=outcome,
        reviewed_at="2026-10-04T12:01:00+00:00"
    )


def _reconciliation(review):
    monitor = _monitor()
    return reconcile_retention_reviews([monitor], [review], expected_review_count=1)


def test_lifecycle_mapping():
    lifecycle = evaluate_retention_review_lifecycle(
        _review(), evaluated_at="2026-10-04T12:02:00+00:00"
    )
    assert lifecycle["lifecycle_state"] == "ACKNOWLEDGED"
    assert lifecycle["decision_executed"] is False
    assert lifecycle["execution_gate_closed"] is True
    assert validate_retention_lifecycle(lifecycle)["lifecycle_fingerprint"] == lifecycle["lifecycle_fingerprint"]


def test_review_retention_maps_to_deferred():
    monitor = _monitor()
    review = review_retention_health(
        monitor, actor_id="reviewer", role="coordinator", outcome="REVIEW_RETENTION",
        reviewed_at="2026-10-04T12:01:00+00:00"
    )
    lifecycle = evaluate_retention_review_lifecycle(review, evaluated_at="2026-10-04T12:02:00+00:00")
    assert lifecycle["lifecycle_state"] == "DEFERRED"


def test_build_bundle_from_reconciled_reviews():
    review = _review()
    reconciliation = _reconciliation(review)
    bundle = build_retention_review_lifecycle(
        reconciliation, [review], evaluated_at="2026-10-04T12:02:00+00:00"
    )
    assert bundle["lifecycle_count"] == 1
    assert bundle["lifecycles"][0]["monitor_fingerprint"] == review["monitor_fingerprint"]


def test_non_reconciled_blocked():
    review = _review()
    bad = _reconciliation(review)
    bad["state"] = "CONTROL_REQUIRED"
    with pytest.raises(ValueError, match="RECONCILIATION_MUST_BE_RECONCILED"):
        build_retention_review_lifecycle(bad, [review], evaluated_at="2026-10-04T12:02:00+00:00")


def test_tampered_lifecycle_rejected():
    lifecycle = evaluate_retention_review_lifecycle(
        _review(), evaluated_at="2026-10-04T12:02:00+00:00"
    )
    lifecycle["lifecycle_state"] = "ESCALATED"
    with pytest.raises(ValueError, match="RETENTION_LIFECYCLE_FINGERPRINT_MISMATCH"):
        validate_retention_lifecycle(lifecycle)
