"""Regression coverage for the phase-159 continuity review reconciliation contract."""
import pytest

from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_continuity_registry_review_reconciliation_phase159 import (
    reconcile_lifecycle_decision_continuity_registry_reviews,
    validate_lifecycle_decision_continuity_registry_review_reconciliation,
)


def test_empty_history_is_explicit_and_execution_remains_closed():
    report = reconcile_lifecycle_decision_continuity_registry_reviews([], [])
    assert report["state"] == "NO_HISTORY"
    assert report["monitor_count"] == 0
    assert report["review_count"] == 0
    assert report["findings"] == []
    assert report["execution_gate_closed"] is True
    assert report["execution_permitted"] is False
    assert report["execution_performed"] is False
    assert validate_lifecycle_decision_continuity_registry_review_reconciliation(report) == report


def test_tampered_execution_control_is_rejected():
    report = reconcile_lifecycle_decision_continuity_registry_reviews([], [])
    report["execution_permitted"] = True
    with pytest.raises(ValueError, match="EXECUTION_GATE_VIOLATION"):
        validate_lifecycle_decision_continuity_registry_review_reconciliation(report)


def test_recomputed_fingerprint_does_not_bypass_count_invariants():
    from nema_agora.api_audit_binding import fingerprint

    report = reconcile_lifecycle_decision_continuity_registry_reviews([], [])
    report["monitor_count"] = -1
    payload = dict(report)
    payload.pop("reconciliation_fingerprint")
    report["reconciliation_fingerprint"] = fingerprint(payload)
    with pytest.raises(ValueError, match="INVALID_RECONCILIATION_COUNTS"):
        validate_lifecycle_decision_continuity_registry_review_reconciliation(report)


def test_recomputed_fingerprint_does_not_bypass_state_invariants():
    from nema_agora.api_audit_binding import fingerprint

    report = reconcile_lifecycle_decision_continuity_registry_reviews([], [])
    report["state"] = "RECONCILED"
    payload = dict(report)
    payload.pop("reconciliation_fingerprint")
    report["reconciliation_fingerprint"] = fingerprint(payload)
    with pytest.raises(ValueError, match="RECONCILIATION_STATE_MISMATCH"):
        validate_lifecycle_decision_continuity_registry_review_reconciliation(report)


def test_reconciliation_requires_explicit_decision_suppression_fields():
    report = reconcile_lifecycle_decision_continuity_registry_reviews([], [])
    del report["environmental_conclusion"]
    with pytest.raises(ValueError, match="RECONCILIATION_FIELDS_REQUIRED"):
        validate_lifecycle_decision_continuity_registry_review_reconciliation(report)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"monitor_reports": None, "reviews": []}, "INVALID_MONITOR_REPORTS"),
        ({"monitor_reports": [], "reviews": "not-a-sequence-of-records"}, "INVALID_REVIEWS"),
        ({"monitor_reports": [], "reviews": [], "expected_review_count": -1}, "INVALID_EXPECTED_REVIEW_COUNT"),
        ({"monitor_reports": [], "reviews": [], "expected_review_count": True}, "INVALID_EXPECTED_REVIEW_COUNT"),
    ],
)
def test_reconciliation_rejects_malformed_inputs(kwargs, message):
    with pytest.raises(ValueError, match=message):
        reconcile_lifecycle_decision_continuity_registry_reviews(**kwargs)
