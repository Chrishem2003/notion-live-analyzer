import pytest
from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_review import review_retention_health
from nema_agora.api_governance_drift_recovery_authorization_retention_lifecycle import evaluate_retention_review_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_decision import authorize_retention_decision
from nema_agora.api_governance_drift_recovery_authorization_retention_decision_reconciliation import reconcile_retention_authorizations, validate_retention_authorization_reconciliation

def _monitor():
    p={"policy_version":"phase117-v1","observed_at":"2026-10-04T12:00:00+00:00","registry_policy_version":"phase116-v1","state":"RETENTION_HEALTHY","snapshot_count":1,"valid_snapshot_count":1,"expected_count":1,"history_state":"HISTORY_READY","history_reconciliation_fingerprint":"synthetic-history","findings":[],"retention_recommendation":"NO_RETENTION_ACTION","read_only":True,"automatic_repair_performed":False,"execution_gate_closed":True,"interpretation":"AUTHORIZATION_RETENTION_INTEGRITY_MONITORING","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None}
    return dict(p,monitor_fingerprint=fingerprint(p))

def _lifecycle(outcome="ACKNOWLEDGED"):
    m=_monitor()
    r=review_retention_health(m,actor_id="reviewer",role="coordinator",outcome=outcome,reviewed_at="2026-10-04T12:01:00+00:00")
    return evaluate_retention_review_lifecycle(r,evaluated_at="2026-10-04T12:02:00+00:00")

def _decision(l):
    return authorize_retention_decision(l,actor_id="admin",role="admin",decision="AUTHORIZE_PRESERVATION",decided_at="2026-10-04T12:03:00+00:00",rationale="Preserve evidence.")

def test_reconciled():
    l=_lifecycle(); d=_decision(l)
    r=reconcile_retention_authorizations([l],[d],expected_decision_count=1)
    assert r["state"]=="RECONCILED"
    assert validate_retention_authorization_reconciliation(r)["reconciliation_fingerprint"]==r["reconciliation_fingerprint"]

def test_unauthorized_lifecycle():
    l=_lifecycle()
    r=reconcile_retention_authorizations([l],[])
    assert r["state"]=="CONTROL_REQUIRED"
    assert any(x["code"]=="UNAUTHORIZED_LIFECYCLE" for x in r["findings"])

def test_orphan_decision():
    l=_lifecycle(); d=_decision(l); d["lifecycle_fingerprint"]="missing"
    d["decision_fingerprint"]=fingerprint({k:v for k,v in d.items() if k!="decision_fingerprint"})
    r=reconcile_retention_authorizations([l],[d])
    assert any(x["code"]=="ORPHAN_DECISION" for x in r["findings"])

def test_binding_mismatch():
    l=_lifecycle(); d=_decision(l); d["monitor_fingerprint"]="wrong"
    d["decision_fingerprint"]=fingerprint({k:v for k,v in d.items() if k!="decision_fingerprint"})
    r=reconcile_retention_authorizations([l],[d])
    assert any(x["code"]=="MONITOR_BINDING_MISMATCH" for x in r["findings"])

def test_duplicate_decision():
    l=_lifecycle(); d=_decision(l)
    r=reconcile_retention_authorizations([l],[d,d])
    assert any(x["code"]=="DUPLICATE_DECISION_FINGERPRINT" for x in r["findings"])
    assert any(x["code"]=="MULTIPLE_DECISIONS_FOR_LIFECYCLE" for x in r["findings"])

def test_execution_gate_tamper():
    l=_lifecycle(); d=_decision(l); d["execution_performed"]=True
    d["decision_fingerprint"]=fingerprint({k:v for k,v in d.items() if k!="decision_fingerprint"})
    r=reconcile_retention_authorizations([l],[d])
    assert any(x["code"]=="EXECUTION_GATE_VIOLATION" for x in r["findings"])

def test_count_mismatch():
    l=_lifecycle(); d=_decision(l)
    r=reconcile_retention_authorizations([l],[d],expected_decision_count=2)
    assert any(x["code"]=="DECISION_COUNT_MISMATCH" for x in r["findings"])
