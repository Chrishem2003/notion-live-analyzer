"""Tests for Phase 147 decision-history continuity."""
from __future__ import annotations
from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_monitor_phase141 import build_authorization_history_registry_decision_history_monitor
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_review_phase142 import review_authorization_history_registry_decision_history
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_review_lifecycle_phase144 import evaluate_authorization_history_registry_decision_history_review_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_phase145 import authorize_authorization_history_registry_decision_history_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_phase147 import (
    build_authorization_history_registry_decision_history_lifecycle_decision_continuity,
    reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity,
    validate_authorization_history_registry_decision_history_lifecycle_decision_continuity,
)
def _decision():
    monitor=build_authorization_history_registry_decision_history_monitor([],expected_count=0,observed_at="2026-10-04T13:00:00+00:00")
    review=review_authorization_history_registry_decision_history(monitor,actor_id="coordinator-147",role="coordinator",outcome="REVIEW_AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY",reviewed_at="2026-10-04T13:05:00+00:00")
    lifecycle=evaluate_authorization_history_registry_decision_history_review_lifecycle(review,evaluated_at="2026-10-04T13:10:00+00:00")
    return authorize_authorization_history_registry_decision_history_lifecycle(lifecycle,actor_id="coordinator-147",role="coordinator",decision="AUTHORIZE_REVIEW",decided_at="2026-10-04T13:15:00+00:00",rationale="Human review is required.")
def _snapshot(seq, prev=None):
    return build_authorization_history_registry_decision_history_lifecycle_decision_continuity([_decision()],captured_at=f"2026-10-04T13:{20+seq:02d}:00+00:00",sequence=seq,previous_snapshot_fingerprint=prev)
def test_first_snapshot_is_ready():
    s=_snapshot(1)
    result=reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity([s])
    assert result["state"]=="HISTORY_READY"
    validate_authorization_history_registry_decision_history_lifecycle_decision_continuity(result)
def test_two_snapshots_with_predecessor_are_ready():
    first=_snapshot(1)
    second=_snapshot(2,first["snapshot_fingerprint"])
    result=reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity([first,second])
    assert result["state"]=="HISTORY_READY"
def test_sequence_gap_detected():
    first=_snapshot(1)
    second=_snapshot(3,first["snapshot_fingerprint"])
    result=reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity([first,second])
    assert any(x["code"]=="SEQUENCE_GAP" for x in result["findings"])
def test_predecessor_mismatch_detected():
    first=_snapshot(1)
    second=_snapshot(2,"wrong")
    result=reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity([first,second])
    assert any(x["code"]=="PREDECESSOR_MISMATCH" for x in result["findings"])
def test_duplicate_sequence_detected():
    first=_snapshot(1)
    result=reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity([first,first])
    assert any(x["code"]=="DUPLICATE_SEQUENCE" for x in result["findings"])
def test_execution_tamper_detected():
    s=_snapshot(1)
    decision=dict(s["decisions"][0]); decision["execution_permitted"]=True
    payload=dict(decision); payload.pop("decision_fingerprint"); decision["decision_fingerprint"]=fingerprint(payload)
    s=dict(s); s["decisions"]=[decision]; payload=dict(s); payload.pop("snapshot_fingerprint"); s["snapshot_fingerprint"]=fingerprint(payload)
    result=reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity([s])
    assert result["state"]=="CONTROL_REQUIRED"
    assert any(x["code"]=="INVALID_SNAPSHOT" for x in result["findings"])
def test_deterministic():
    s=_snapshot(1)
    a=reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity([s])
    b=reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity([s])
    assert a["reconciliation_fingerprint"]==b["reconciliation_fingerprint"]
