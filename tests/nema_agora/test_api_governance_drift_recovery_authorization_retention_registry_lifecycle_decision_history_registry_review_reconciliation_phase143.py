"""Tests for Phase 143 review reconciliation."""
from __future__ import annotations

from copy import deepcopy

from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_monitor_phase141 import build_authorization_history_registry_decision_history_monitor
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_review_phase142 import review_authorization_history_registry_decision_history
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_review_reconciliation_phase143 import (
    reconcile_authorization_history_registry_decision_history_reviews,
    validate_authorization_history_registry_decision_history_review_reconciliation,
)

def _monitor():
    return build_authorization_history_registry_decision_history_monitor([], expected_count=0, observed_at="2026-10-04T13:00:00+00:00")

def _review():
    return review_authorization_history_registry_decision_history(
        _monitor(), actor_id="coordinator-143", role="coordinator",
        outcome="REVIEW_AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY",
        reviewed_at="2026-10-04T13:05:00+00:00",
    )

def test_reconciled_monitor_and_review():
    monitor = _monitor()
    review = _review()
    result = reconcile_authorization_history_registry_decision_history_reviews([monitor], [review], expected_review_count=1)
    assert result["state"] == "RECONCILED"
    validate_authorization_history_registry_decision_history_review_reconciliation(result)

def test_unreviewed_monitor_requires_control():
    result = reconcile_authorization_history_registry_decision_history_reviews([_monitor()], [], expected_review_count=0)
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "UNREVIEWED_MONITOR" for x in result["findings"])

def test_orphan_review_requires_control():
    monitor = _monitor()
    orphan = _review()
    orphan["monitor_fingerprint"] = "orphan"
    from nema_agora.api_audit_binding import fingerprint
    payload = dict(orphan)
    payload.pop("review_fingerprint")
    orphan["review_fingerprint"] = fingerprint(payload)
    result = reconcile_authorization_history_registry_decision_history_reviews([monitor], [orphan], expected_review_count=1)
    assert any(x["code"] == "ORPHAN_REVIEW" for x in result["findings"])

def test_multiple_reviews_require_control():
    monitor = _monitor()
    review = _review()
    second = deepcopy(review)
    second["reviewed_at"] = "2026-10-04T13:06:00+00:00"
    from nema_agora.api_audit_binding import fingerprint
    payload = dict(second)
    payload.pop("review_fingerprint")
    second["review_fingerprint"] = fingerprint(payload)
    result = reconcile_authorization_history_registry_decision_history_reviews([monitor], [review, second], expected_review_count=2)
    assert any(x["code"] == "MULTIPLE_REVIEWS_FOR_MONITOR" for x in result["findings"])

def test_binding_mismatch_requires_control():
    monitor = _monitor()
    review = _review()
    review["monitor_state"] = "CONTROL_REQUIRED"
    from nema_agora.api_audit_binding import fingerprint
    payload = dict(review)
    payload.pop("review_fingerprint")
    review["review_fingerprint"] = fingerprint(payload)
    result = reconcile_authorization_history_registry_decision_history_reviews([monitor], [review])
    assert any(x["code"] == "MONITOR_STATE_MISMATCH" for x in result["findings"])

def test_execution_tamper_is_invalid_review():
    monitor = _monitor()
    review = _review()
    review["execution_performed"] = True
    from nema_agora.api_audit_binding import fingerprint
    payload = dict(review)
    payload.pop("review_fingerprint")
    review["review_fingerprint"] = fingerprint(payload)
    result = reconcile_authorization_history_registry_decision_history_reviews([monitor], [review])
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "INVALID_REVIEW" for x in result["findings"])

def test_reconciliation_is_deterministic():
    result_a = reconcile_authorization_history_registry_decision_history_reviews([_monitor()], [], expected_review_count=0)
    result_b = reconcile_authorization_history_registry_decision_history_reviews([_monitor()], [], expected_review_count=0)
    assert result_a["reconciliation_fingerprint"] == result_b["reconciliation_fingerprint"]
