"""Regression coverage for the phase-159 continuity review reconciliation contract."""
import importlib

import pytest

MODULE_NAME = (
    "nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_"
    "registry_lifecycle_decision_continuity_review_lifecycle_decision_continuity_registry_review_reconciliation_phase159"
)
module = importlib.import_module(MODULE_NAME)


def test_empty_history_is_explicit_and_execution_remains_closed():
    report = module.reconcile_lifecycle_decision_continuity_registry_reviews([], [])
    assert report["state"] == "NO_HISTORY"
    assert report["monitor_count"] == 0
    assert report["review_count"] == 0
    assert report["findings"] == []
    assert report["execution_gate_closed"] is True
    assert report["execution_permitted"] is False
    assert report["execution_performed"] is False
    assert module.validate_lifecycle_decision_continuity_registry_review_reconciliation(report) == report


def test_tampered_execution_control_is_rejected():
    report = module.reconcile_lifecycle_decision_continuity_registry_reviews([], [])
    report["execution_permitted"] = True
    with pytest.raises(ValueError, match="EXECUTION_GATE_VIOLATION"):
        module.validate_lifecycle_decision_continuity_registry_review_reconciliation(report)
