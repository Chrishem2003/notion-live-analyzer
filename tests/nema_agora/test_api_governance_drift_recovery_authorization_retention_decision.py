import pytest
from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_review import review_retention_health
from nema_agora.api_governance_drift_recovery_authorization_retention_lifecycle import evaluate_retention_review_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_decision import authorize_retention_decision, validate_retention_decision

def _monitor(state="RETENTION_HEALTHY"):
    p={"policy_version":"phase117-v1","observed_at":"2026-10-04T12:00:00+00:00","registry_policy_version":"phase116-v1","state":state,"snapshot_count":1 if state=="RETENTION_HEALTHY" else 0,"valid_snapshot_count":1 if state=="RETENTION_HEALTHY" else 0,"expected_count":1 if state=="RETENTION_HEALTHY" else 0,"history_state":"HISTORY_READY" if state=="RETENTION_HEALTHY" else "NO_HISTORY","history_reconciliation_fingerprint":"synthetic-history","findings":[] if state=="RETENTION_HEALTHY" else [{"code":"CONTROL_REQUIRED"}],"retention_recommendation":"NO_RETENTION_ACTION" if state=="RETENTION_HEALTHY" else "REVIEW_RETENTION","read_only":True,"automatic_repair_performed":False,"execution_gate_closed":True,"interpretation":"AUTHORIZATION_RETENTION_INTEGRITY_MONITORING","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None}
    return dict(p,monitor_fingerprint=fingerprint(p))

def _lifecycle(outcome="ACKNOWLEDGED"):
    m=_monitor()
    r=review_retention_health(m,actor_id="reviewer",role="coordinator",outcome=outcome,reviewed_at="2026-10-04T12:01:00+00:00")
    return evaluate_retention_review_lifecycle(r,evaluated_at="2026-10-04T12:02:00+00:00")

def test_preservation_authorization():
    d=authorize_retention_decision(_lifecycle(),actor_id="admin",role="admin",decision="AUTHORIZE_PRESERVATION",decided_at="2026-10-04T12:03:00+00:00",rationale="Preserve evidence.")
    assert d["human_authorized"] is True and d["execution_permitted"] is False
    assert validate_retention_decision(d)["decision_fingerprint"] == d["decision_fingerprint"]

def test_tampered_decision_rejected():
    d=authorize_retention_decision(_lifecycle(),actor_id="admin",role="admin",decision="AUTHORIZE_PRESERVATION",decided_at="2026-10-04T12:03:00+00:00",rationale="Preserve evidence.")
    d["execution_performed"]=True
    with pytest.raises(ValueError,match="RETENTION_DECISION_FINGERPRINT_MISMATCH"): validate_retention_decision(d)

def test_escalation_requires_escalated_lifecycle():
    with pytest.raises(ValueError,match="ESCALATION_REQUIRES_ESCALATED"):
        authorize_retention_decision(_lifecycle(),actor_id="admin",role="admin",decision="AUTHORIZE_ESCALATION",decided_at="2026-10-04T12:03:00+00:00",rationale="Escalate.")
