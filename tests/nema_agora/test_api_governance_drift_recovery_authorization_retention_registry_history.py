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
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_history import (
    build_retention_registry_authorization_continuity,
    reconcile_retention_registry_authorization_history,
    validate_retention_registry_authorization_snapshot,
    validate_retention_registry_authorization_history_reconciliation,
)


def _monitor():
    p={"policy_version":"phase125-v1","observed_at":"2026-10-04T12:00:00+00:00","registry_policy_version":"phase124-v1","state":"RETENTION_REGISTRY_HEALTHY","snapshot_count":1,"valid_snapshot_count":1,"expected_count":1,"history_state":"HISTORY_READY","history_reconciliation_fingerprint":"h","findings":[],"retention_registry_recommendation":"NO_RETENTION_REGISTRY_ACTION","read_only":True,"human_governed":True,"automatic_repair_performed":False,"execution_gate_closed":True,"execution_permitted":False,"execution_performed":False,"interpretation":"x","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None,"emergency_action":None}
    return dict(p,monitor_fingerprint=fingerprint(p))


def _decision():
    review=review_retention_registry(_monitor(),actor_id="reviewer",role="coordinator",outcome="ACKNOWLEDGED",reviewed_at="2026-10-04T12:01:00+00:00")
    lifecycle=evaluate_retention_registry_review_lifecycle(review,evaluated_at="2026-10-04T12:02:00+00:00")
    return authorize_retention_registry_decision(lifecycle,actor_id="admin",role="admin",decision="AUTHORIZE_PRESERVATION",decided_at="2026-10-04T12:03:00+00:00",rationale="Preserve reviewed evidence.")


def test_continuity_and_validation():
    decision=_decision()
    snapshot=build_retention_registry_authorization_continuity([decision],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    assert snapshot["decision_count"]==1
    assert validate_retention_registry_authorization_snapshot(snapshot)==snapshot


def test_history_ready_and_deterministic():
    decision=_decision()
    a=build_retention_registry_authorization_continuity([decision],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    b=build_retention_registry_authorization_continuity([decision],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    r=reconcile_retention_registry_authorization_history([a])
    assert r["state"]=="HISTORY_READY"
    assert r["reconciliation_fingerprint"]==reconcile_retention_registry_authorization_history([b])["reconciliation_fingerprint"]
    assert validate_retention_registry_authorization_history_reconciliation(r)==r


def test_empty_history():
    assert reconcile_retention_registry_authorization_history([])["state"]=="NO_HISTORY"


def test_history_must_start_at_one():
    decision=_decision()
    s=build_retention_registry_authorization_continuity([decision],captured_at="2026-10-04T12:04:00+00:00",sequence=2)
    r=reconcile_retention_registry_authorization_history([s])
    assert any(x["code"]=="HISTORY_MUST_START_AT_ONE" for x in r["findings"])


def test_predecessor_and_gap():
    decision=_decision()
    first=build_retention_registry_authorization_continuity([decision],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    second=build_retention_registry_authorization_continuity([decision],captured_at="2026-10-04T12:05:00+00:00",sequence=3,previous_snapshot_fingerprint=first["snapshot_fingerprint"])
    r=reconcile_retention_registry_authorization_history([first,second])
    assert any(x["code"]=="SEQUENCE_GAP" for x in r["findings"])


def test_predecessor_mismatch():
    decision=_decision()
    first=build_retention_registry_authorization_continuity([decision],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    second=build_retention_registry_authorization_continuity([decision],captured_at="2026-10-04T12:05:00+00:00",sequence=2,previous_snapshot_fingerprint="wrong")
    r=reconcile_retention_registry_authorization_history([first,second])
    assert any(x["code"]=="PREDECESSOR_MISMATCH" for x in r["findings"])


def test_tampered_snapshot_rejected():
    decision=_decision()
    s=build_retention_registry_authorization_continuity([decision],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    s["execution_gate_closed"]=False
    r=reconcile_retention_registry_authorization_history([s])
    assert any(x["code"]=="INVALID_SNAPSHOT" for x in r["findings"])


def test_duplicate_decision_identity():
    with pytest.raises(ValueError, match="DUPLICATE_DECISION_IDENTITY"):
        build_retention_registry_authorization_continuity([_decision(),_decision()],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
