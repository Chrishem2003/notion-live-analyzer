import pytest

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle import (
    evaluate_retention_registry_review_lifecycle,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_review import (
    review_retention_registry,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_decision import (
    authorize_retention_registry_decision,
    validate_retention_registry_decision,
)


def _monitor(state):
    rec = {"RETENTION_REGISTRY_HEALTHY":"NO_RETENTION_REGISTRY_ACTION","NO_HISTORY":"REVIEW_RETENTION_REGISTRY","CONTROL_REQUIRED":"PRESERVE_AND_ESCALATE"}[state]
    p={"policy_version":"phase125-v1","observed_at":"2026-10-04T12:00:00+00:00","registry_policy_version":"phase124-v1","state":state,"snapshot_count":0 if state=="NO_HISTORY" else 1,"valid_snapshot_count":0 if state=="NO_HISTORY" else 1,"expected_count":0 if state=="NO_HISTORY" else 1,"history_state":"NO_HISTORY" if state=="NO_HISTORY" else "HISTORY_READY","history_reconciliation_fingerprint":"h","findings":[],"retention_registry_recommendation":rec,"read_only":True,"human_governed":True,"automatic_repair_performed":False,"execution_gate_closed":True,"execution_permitted":False,"execution_performed":False,"interpretation":"x","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None,"emergency_action":None}
    return dict(p,monitor_fingerprint=fingerprint(p))

def _lifecycle(state):
    outcomes={"RETENTION_REGISTRY_HEALTHY":"ACKNOWLEDGED","NO_HISTORY":"REVIEW_RETENTION_REGISTRY","CONTROL_REQUIRED":"PRESERVE_AND_ESCALATE"}
    review=review_retention_registry(_monitor(state),actor_id="reviewer",role="coordinator",outcome=outcomes[state],reviewed_at="2026-10-04T12:01:00+00:00")
    return evaluate_retention_registry_review_lifecycle(review,evaluated_at="2026-10-04T12:02:00+00:00")

def test_acknowledged_can_authorize_preservation():
    d=authorize_retention_registry_decision(_lifecycle("RETENTION_REGISTRY_HEALTHY"),actor_id="admin",role="admin",decision="AUTHORIZE_PRESERVATION",decided_at="2026-10-04T12:03:00+00:00",rationale="Preserve reviewed evidence.")
    assert d["human_authorized"] is True and d["execution_permitted"] is False
    assert validate_retention_registry_decision(d)==d

def test_deferred_can_authorize_review_or_preservation():
    lifecycle=_lifecycle("NO_HISTORY")
    for choice in ("AUTHORIZE_RETENTION_REVIEW","AUTHORIZE_PRESERVATION"):
        d=authorize_retention_registry_decision(lifecycle,actor_id="admin",role="admin",decision=choice,decided_at="2026-10-04T12:03:00+00:00",rationale="Human review authorization.")

def test_escalated_requires_escalation():
    d=authorize_retention_registry_decision(_lifecycle("CONTROL_REQUIRED"),actor_id="admin",role="admin",decision="AUTHORIZE_ESCALATION",decided_at="2026-10-04T12:03:00+00:00",rationale="Escalate for controlled review.")
    assert d["decision"]=="AUTHORIZE_ESCALATION"

def test_invalid_state_decision_blocked():
    with pytest.raises(ValueError,match="DECISION_LIFECYCLE_STATE_MISMATCH"):
        authorize_retention_registry_decision(_lifecycle("CONTROL_REQUIRED"),actor_id="admin",role="admin",decision="AUTHORIZE_PRESERVATION",decided_at="2026-10-04T12:03:00+00:00",rationale="bad")

def test_tampered_decision_rejected():
    d=authorize_retention_registry_decision(_lifecycle("RETENTION_REGISTRY_HEALTHY"),actor_id="admin",role="admin",decision="AUTHORIZE_PRESERVATION",decided_at="2026-10-04T12:03:00+00:00",rationale="Preserve.")
    d["execution_performed"]=True
    with pytest.raises(ValueError,match="EXECUTION_MUST_REMAIN_FORBIDDEN"):
        validate_retention_registry_decision(d)
