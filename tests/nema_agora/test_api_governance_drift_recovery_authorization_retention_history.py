from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_review import review_retention_health
from nema_agora.api_governance_drift_recovery_authorization_retention_lifecycle import evaluate_retention_review_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_decision import authorize_retention_decision
from nema_agora.api_governance_drift_recovery_authorization_retention_history import (
    build_retention_authorization_continuity,
    validate_retention_authorization_snapshot,
    reconcile_retention_authorization_history,
)

def _decision():
    p={"policy_version":"phase117-v1","observed_at":"2026-10-04T12:00:00+00:00","registry_policy_version":"phase116-v1","state":"RETENTION_HEALTHY","snapshot_count":1,"valid_snapshot_count":1,"expected_count":1,"history_state":"HISTORY_READY","history_reconciliation_fingerprint":"synthetic-history","findings":[],"retention_recommendation":"NO_RETENTION_ACTION","read_only":True,"automatic_repair_performed":False,"execution_gate_closed":True,"interpretation":"AUTHORIZATION_RETENTION_INTEGRITY_MONITORING","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None}
    m=dict(p,monitor_fingerprint=fingerprint(p))
    r=review_retention_health(m,actor_id="reviewer",role="coordinator",outcome="ACKNOWLEDGED",reviewed_at="2026-10-04T12:01:00+00:00")
    l=evaluate_retention_review_lifecycle(r,evaluated_at="2026-10-04T12:02:00+00:00")
    return authorize_retention_decision(l,actor_id="admin",role="admin",decision="AUTHORIZE_PRESERVATION",decided_at="2026-10-04T12:03:00+00:00",rationale="Preserve evidence.")

def test_continuity_ready():
    s=build_retention_authorization_continuity([_decision()],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    assert reconcile_retention_authorization_history([s])["state"]=="HISTORY_READY"
    assert validate_retention_authorization_snapshot(s)["snapshot_fingerprint"]==s["snapshot_fingerprint"]

def test_empty_history():
    assert reconcile_retention_authorization_history([])["state"]=="NO_HISTORY"

def test_history_must_start_at_one():
    s=build_retention_authorization_continuity([_decision()],captured_at="2026-10-04T12:04:00+00:00",sequence=2)
    r=reconcile_retention_authorization_history([s])
    assert r["state"]=="CONTROL_REQUIRED"
    assert any(x["code"]=="HISTORY_MUST_START_AT_ONE" for x in r["findings"])

def test_predecessor_mismatch():
    d=_decision()
    s1=build_retention_authorization_continuity([d],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    s2=build_retention_authorization_continuity([d],captured_at="2026-10-04T12:05:00+00:00",sequence=2,previous_snapshot_fingerprint="wrong")
    r=reconcile_retention_authorization_history([s1,s2])
    assert any(x["code"]=="PREDECESSOR_MISMATCH" for x in r["findings"])

def test_tampered_snapshot_rejected():
    s=build_retention_authorization_continuity([_decision()],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    s["execution_performed"]=True
    s["snapshot_fingerprint"]=fingerprint({k:v for k,v in s.items() if k!="snapshot_fingerprint"})
    r=reconcile_retention_authorization_history([s])
    assert any(x["code"]=="INVALID_SNAPSHOT" for x in r["findings"])

def test_duplicate_decisions_rejected():
    d=_decision()
    try:
        build_retention_authorization_continuity([d,d],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    except ValueError as exc:
        assert str(exc)=="DUPLICATE_DECISION_IDENTITY"
    else:
        raise AssertionError("duplicate decisions must be rejected")

def test_deterministic():
    s=build_retention_authorization_continuity([_decision()],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    a=reconcile_retention_authorization_history([s])
    b=reconcile_retention_authorization_history([s])
    assert a["reconciliation_fingerprint"]==b["reconciliation_fingerprint"]
