"""Phase 154 tests — lifecycle decision reconciliation."""
from __future__ import annotations
import pytest
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_phase147 import build_authorization_history_registry_decision_history_lifecycle_decision_continuity
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_monitor_phase149 import build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_phase150 import review_authorization_history_registry_decision_history_lifecycle_decision_continuity
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_phase152 import evaluate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_phase153 import authorize_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_reconciliation_phase154 import reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decisions, validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_reconciliation

def pair(outcome="ACKNOWLEDGED"):
    s = build_authorization_history_registry_decision_history_lifecycle_decision_continuity([], captured_at="2026-10-04T09:00:00+00:00", sequence=1)
    m = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor([s], expected_count=1, observed_at="2026-10-04T10:00:00+00:00")
    r = review_authorization_history_registry_decision_history_lifecycle_decision_continuity(m, actor_id="reviewer", role="coordinator", outcome=outcome, reviewed_at="2026-10-04T11:00:00+00:00")
    l = evaluate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(r, evaluated_at="2026-10-04T12:00:00+00:00")
    d = authorize_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(l, actor_id="admin", role="admin", decision="AUTHORIZE_PRESERVATION" if outcome == "ACKNOWLEDGED" else "AUTHORIZE_REVIEW", decided_at="2026-10-04T13:00:00+00:00", rationale="Human governance decision.")
    return l, d

def test_reconciled_pair():
    l, d = pair()
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decisions([l], [d], expected_decision_count=1)
    assert result["state"] == "RECONCILED", result["findings"]
    assert validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_reconciliation(result) == result

def test_unreviewed_lifecycle_requires_control():
    l, _ = pair()
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decisions([l], [])
    assert result["state"] == "CONTROL_REQUIRED"
    assert "LIFECYCLE_WITHOUT_DECISION" in result["findings"]

def test_orphan_decision_requires_control():
    l, d = pair()
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decisions([], [d])
    assert result["state"] == "CONTROL_REQUIRED"
    assert "ORPHAN_DECISION" in result["findings"]

def test_tampered_decision_is_invalid():
    l, d = pair()
    bad = dict(d, lifecycle_fingerprint="tampered")
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decisions([l], [bad])
    assert result["state"] == "CONTROL_REQUIRED"
    assert "INVALID_DECISION" in result["findings"]

def test_execution_boundary_is_detected():
    l, d = pair()
    bad = dict(d, execution_performed=True)
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decisions([l], [bad])
    assert result["state"] == "CONTROL_REQUIRED"
    assert "INVALID_DECISION" in result["findings"]
