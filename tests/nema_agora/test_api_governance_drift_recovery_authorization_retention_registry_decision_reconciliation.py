import pytest

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_decision import (
    authorize_retention_registry_decision,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle import (
    evaluate_retention_registry_review_lifecycle,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_review import (
    review_retention_registry,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_decision_reconciliation import (
    reconcile_retention_registry_decisions,
    validate_retention_registry_decision_reconciliation,
)


def _monitor():
    p={"policy_version":"phase125-v1","observed_at":"2026-10-04T12:00:00+00:00","registry_policy_version":"phase124-v1","state":"RETENTION_REGISTRY_HEALTHY","snapshot_count":1,"valid_snapshot_count":1,"expected_count":1,"history_state":"HISTORY_READY","history_reconciliation_fingerprint":"h","findings":[],"retention_registry_recommendation":"NO_RETENTION_REGISTRY_ACTION","read_only":True,"human_governed":True,"automatic_repair_performed":False,"execution_gate_closed":True,"execution_permitted":False,"execution_performed":False,"interpretation":"x","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None,"emergency_action":None}
    return dict(p,monitor_fingerprint=fingerprint(p))


def _lifecycle():
    review=review_retention_registry(_monitor(),actor_id="reviewer",role="coordinator",outcome="ACKNOWLEDGED",reviewed_at="2026-10-04T12:01:00+00:00")
    return evaluate_retention_registry_review_lifecycle(review,evaluated_at="2026-10-04T12:02:00+00:00")


def _decision():
    return authorize_retention_registry_decision(_lifecycle(),actor_id="admin",role="admin",decision="AUTHORIZE_PRESERVATION",decided_at="2026-10-04T12:03:00+00:00",rationale="Preserve reviewed evidence.")


def test_reconciled():
    lifecycle=_lifecycle()
    decision=authorize_retention_registry_decision(lifecycle,actor_id="admin",role="admin",decision="AUTHORIZE_PRESERVATION",decided_at="2026-10-04T12:03:00+00:00",rationale="Preserve reviewed evidence.")
    result=reconcile_retention_registry_decisions([lifecycle],[decision],expected_decision_count=1)
    assert result["state"]=="RECONCILED"
    assert result["findings"]==[]
    assert validate_retention_registry_decision_reconciliation(result)==result


def test_unauthorized_lifecycle():
    result=reconcile_retention_registry_decisions([_lifecycle()],[],expected_decision_count=0)
    assert result["state"]=="CONTROL_REQUIRED"
    assert any(x["code"]=="UNAUTHORIZED_LIFECYCLE" for x in result["findings"])


def test_orphan_decision():
    result=reconcile_retention_registry_decisions([],[_decision()],expected_decision_count=1)
    assert result["state"]=="CONTROL_REQUIRED"
    assert any(x["code"]=="ORPHAN_DECISION" for x in result["findings"])


def test_binding_mismatch():
    lifecycle=_lifecycle()
    decision=dict(_decision())
    decision["lifecycle_fingerprint"]="wrong"
    result=reconcile_retention_registry_decisions([lifecycle],[decision])
    assert result["state"]=="CONTROL_REQUIRED"


def test_duplicate_decision():
    lifecycle=_lifecycle()
    decision=_decision()
    result=reconcile_retention_registry_decisions([lifecycle],[decision,decision])
    assert any(x["code"]=="DUPLICATE_DECISION_FINGERPRINT" for x in result["findings"])
    assert any(x["code"]=="MULTIPLE_DECISIONS_FOR_LIFECYCLE" for x in result["findings"])


def test_execution_tamper_is_invalid():
    decision=_decision()
    decision["execution_performed"]=True
    result=reconcile_retention_registry_decisions([_lifecycle()],[decision])
    assert any(x["code"]=="INVALID_DECISION" for x in result["findings"])


def test_count_mismatch():
    result=reconcile_retention_registry_decisions([_lifecycle()],[_decision()],expected_decision_count=2)
    assert any(x["code"]=="DECISION_COUNT_MISMATCH" for x in result["findings"])
