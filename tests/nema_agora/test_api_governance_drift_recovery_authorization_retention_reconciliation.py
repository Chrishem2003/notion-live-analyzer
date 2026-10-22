import pytest

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_reconciliation import (
    reconcile_retention_reviews,
    validate_retention_reconciliation,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_review import (
    review_retention_health,
)


def _monitor(state="RETENTION_HEALTHY", recommendation="NO_RETENTION_ACTION"):
    payload = {
        "policy_version": "phase117-v1",
        "observed_at": "2026-10-04T12:00:00+00:00",
        "registry_policy_version": "phase116-v1",
        "state": state,
        "snapshot_count": 1 if state == "RETENTION_HEALTHY" else 0,
        "valid_snapshot_count": 1 if state == "RETENTION_HEALTHY" else 0,
        "expected_count": 1 if state == "RETENTION_HEALTHY" else 0,
        "history_state": "HISTORY_READY" if state == "RETENTION_HEALTHY" else "NO_HISTORY",
        "history_reconciliation_fingerprint": "synthetic-history",
        "findings": [] if state == "RETENTION_HEALTHY" else [{"code": "CONTROL_REQUIRED"}],
        "retention_recommendation": recommendation,
        "read_only": True, "automatic_repair_performed": False, "execution_gate_closed": True,
        "interpretation": "AUTHORIZATION_RETENTION_INTEGRITY_MONITORING",
        "environmental_conclusion": None, "regulatory_conclusion": None, "enforcement_action": None,
    }
    return dict(payload, monitor_fingerprint=fingerprint(payload))


def test_reconciled():
    monitor = _monitor()
    review = review_retention_health(
        monitor, actor_id="reviewer", role="coordinator",
        outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:01:00+00:00"
    )
    result = reconcile_retention_reviews([monitor], [review], expected_review_count=1)
    assert result["state"] == "RECONCILED"
    assert validate_retention_reconciliation(result)["reconciliation_fingerprint"] == result["reconciliation_fingerprint"]


def test_unreviewed_monitor():
    result = reconcile_retention_reviews([_monitor()], [], expected_review_count=0)
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "UNREVIEWED_MONITOR" for x in result["findings"])


def test_orphan_review():
    monitor = _monitor()
    review = review_retention_health(
        monitor, actor_id="reviewer", role="coordinator",
        outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:01:00+00:00"
    )
    result = reconcile_retention_reviews([], [review], expected_review_count=1)
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "ORPHAN_REVIEW" for x in result["findings"])


def test_duplicate_review():
    monitor = _monitor()
    review = review_retention_health(
        monitor, actor_id="reviewer", role="coordinator",
        outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:01:00+00:00"
    )
    result = reconcile_retention_reviews([monitor], [review, review], expected_review_count=2)
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "MULTIPLE_REVIEWS_FOR_MONITOR" for x in result["findings"])


def test_tampered_review():
    monitor = _monitor()
    review = review_retention_health(
        monitor, actor_id="reviewer", role="coordinator",
        outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:01:00+00:00"
    )
    review["monitor_state"] = "CONTROL_REQUIRED"
    result = reconcile_retention_reviews([monitor], [review])
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "INVALID_REVIEW" for x in result["findings"])


def test_count_mismatch():
    result = reconcile_retention_reviews([], [], expected_review_count=1)
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "REVIEW_COUNT_MISMATCH" for x in result["findings"])
