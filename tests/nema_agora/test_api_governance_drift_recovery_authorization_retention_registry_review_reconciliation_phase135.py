import pytest

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_registry_monitor import build_retention_registry_authorization_registry_monitor
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_review_phase134 import review_authorization_history_registry
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_review_reconciliation_phase135 import (
    reconcile_authorization_history_registry_reviews,
    validate_authorization_history_registry_review_reconciliation,
)


def _monitor(expected_count=1):
    return build_retention_registry_authorization_registry_monitor(
        [], expected_count=expected_count, observed_at="2026-10-04T12:00:00+00:00"
    )


def _review(monitor):
    return review_authorization_history_registry(
        monitor,
        actor_id="reviewer",
        role="coordinator",
        outcome="REVIEW_AUTHORIZATION_HISTORY_REGISTRY",
        reviewed_at="2026-10-04T12:01:00+00:00",
    )


def test_reconciled():
    monitor = _monitor()
    review = _review(monitor)
    result = reconcile_authorization_history_registry_reviews([monitor], [review], expected_review_count=1)
    assert result["state"] == "RECONCILED"
    assert result["findings"] == []
    assert validate_authorization_history_registry_review_reconciliation(result) == result


def test_unreviewed_monitor():
    monitor = _monitor()
    result = reconcile_authorization_history_registry_reviews([monitor], [], expected_review_count=0)
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "UNREVIEWED_MONITOR" for x in result["findings"])


def test_orphan_review():
    monitor = _monitor()
    review = _review(monitor)
    orphan = dict(review, monitor_fingerprint="missing")
    payload = dict(orphan)
    payload.pop("review_fingerprint")
    orphan["review_fingerprint"] = fingerprint(payload)
    result = reconcile_authorization_history_registry_reviews([monitor], [orphan])
    assert any(x["code"] == "ORPHAN_REVIEW" for x in result["findings"])


def test_multiple_reviews():
    monitor = _monitor()
    review = _review(monitor)
    result = reconcile_authorization_history_registry_reviews([monitor], [review, review])
    assert any(x["code"] == "DUPLICATE_REVIEW_FINGERPRINT" for x in result["findings"])
    assert any(x["code"] == "MULTIPLE_REVIEWS_FOR_MONITOR" for x in result["findings"])


def test_binding_mismatch():
    monitor = _monitor()
    review = _review(monitor)
    changed = dict(review, monitor_state="RETENTION_REGISTRY_HEALTHY")
    payload = dict(changed)
    payload.pop("review_fingerprint")
    changed["review_fingerprint"] = fingerprint(payload)
    result = reconcile_authorization_history_registry_reviews([monitor], [changed])
    assert any(x["code"] == "MONITOR_STATE_MISMATCH" for x in result["findings"])


def test_count_mismatch():
    monitor = _monitor()
    review = _review(monitor)
    result = reconcile_authorization_history_registry_reviews([monitor], [review], expected_review_count=2)
    assert any(x["code"] == "REVIEW_COUNT_MISMATCH" for x in result["findings"])


def test_execution_tamper():
    monitor = _monitor()
    review = _review(monitor)
    changed = dict(review, execution_performed=True)
    result = reconcile_authorization_history_registry_reviews([monitor], [changed])
    assert any(x["code"] == "INVALID_REVIEW" for x in result["findings"])
