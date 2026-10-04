"""Tests for Phase 146 lifecycle-decision reconciliation."""
from __future__ import annotations
from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_monitor_phase141 import build_authorization_history_registry_decision_history_monitor
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_review_phase142 import review_authorization_history_registry_decision_history
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_review_lifecycle_phase144 import evaluate_authorization_history_registry_decision_history_review_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_phase145 import authorize_authorization_history_registry_decision_history_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_reconciliation_phase146 import reconcile_authorization_history_registry_decision_history_lifecycle_decisions, validate_authorization_history_registry_decision_history_lifecycle_decision_reconciliation

def _monitor():
    return build_authorization_history_registry_decision_history_monitor([], expected_count=0, observed_at="2026-10-04T13:00:00+00:00")

def _review():
    return review_authorization_history_registry_decision_history(_monitor(), actor_id="coordinator-146", role="coordinator", outcome="REVIEW_AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY", reviewed_at="2026-10-04T13:05:00+00:00")

def _lifecycle():
    return evaluate_authorization_history_registry_decision_history_review_lifecycle(_review(), evaluated_at="2026-10-04T13:10:00+00:00")

def _decision(lifecycle=None):
    return authorize_authorization_history_registry_decision_history_lifecycle(lifecycle or _lifecycle(), actor_id="coordinator-146", role="coordinator", decision="AUTHORIZE_REVIEW", decided_at="2026-10-04T13:15:00+00:00", rationale="Human review is required before preservation.")

def test_reconciled_lifecycle_and_decision():
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decisions([_lifecycle()], [_decision()], expected_decision_count=1)
    assert result["state"] == "RECONCILED"
    assert result["findings"] == []
    validate_authorization_history_registry_decision_history_lifecycle_decision_reconciliation(result)

def test_lifecycle_without_decision():
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decisions([_lifecycle()], [], expected_decision_count=0)
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "LIFECYCLE_WITHOUT_DECISION" for x in result["findings"])

def test_orphan_decision():
    lifecycle = _lifecycle()
    decision = _decision(lifecycle)
    decision["lifecycle_fingerprint"] = "orphan"
    payload = dict(decision)
    payload.pop("decision_fingerprint")
    decision["decision_fingerprint"] = fingerprint(payload)
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decisions([lifecycle], [decision], expected_decision_count=1)
    assert any(x["code"] == "ORPHAN_DECISION" for x in result["findings"])

def test_multiple_decisions_for_lifecycle():
    lifecycle = _lifecycle()
    decision = _decision(lifecycle)
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decisions([lifecycle], [decision, decision], expected_decision_count=2)
    assert any(x["code"] == "MULTIPLE_DECISIONS_FOR_LIFECYCLE" for x in result["findings"])
    assert any(x["code"] == "DUPLICATE_DECISION_FINGERPRINT" for x in result["findings"])

def test_binding_mismatch():
    lifecycle = _lifecycle()
    decision = _decision(lifecycle)
    decision["review_fingerprint"] = "wrong-review"
    payload = dict(decision)
    payload.pop("decision_fingerprint")
    decision["decision_fingerprint"] = fingerprint(payload)
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decisions([lifecycle], [decision], expected_decision_count=1)
    assert any(x["code"] == "REVIEW_BINDING_MISMATCH" for x in result["findings"])

def test_count_mismatch():
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decisions([_lifecycle()], [_decision()], expected_decision_count=2)
    assert any(x["code"] == "DECISION_COUNT_MISMATCH" for x in result["findings"])

def test_execution_tamper_is_rejected_by_upstream_validator():
    decision = _decision()
    decision["execution_permitted"] = True
    payload = dict(decision)
    payload.pop("decision_fingerprint")
    decision["decision_fingerprint"] = fingerprint(payload)
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decisions([_lifecycle()], [decision], expected_decision_count=1)
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "INVALID_DECISION" for x in result["findings"])

def test_deterministic_reconciliation():
    lifecycle = _lifecycle()
    decision = _decision(lifecycle)
    first = reconcile_authorization_history_registry_decision_history_lifecycle_decisions([lifecycle], [decision], expected_decision_count=1)
    second = reconcile_authorization_history_registry_decision_history_lifecycle_decisions([lifecycle], [decision], expected_decision_count=1)
    assert first["reconciliation_fingerprint"] == second["reconciliation_fingerprint"]
