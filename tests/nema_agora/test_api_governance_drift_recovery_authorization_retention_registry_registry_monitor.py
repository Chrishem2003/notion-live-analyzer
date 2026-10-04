import pytest

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_decision import authorize_retention_registry_decision
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_history import build_retention_registry_authorization_continuity
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle import evaluate_retention_registry_review_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_registry import RetentionRegistryAuthorizationHistoryRegistry
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_review import review_retention_registry
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_registry_monitor import (
    build_retention_registry_authorization_registry_monitor,
    monitor_registry,
    validate_retention_registry_authorization_registry_monitor,
)


def _decision():
    p={"policy_version":"phase125-v1","observed_at":"2026-10-04T12:00:00+00:00","registry_policy_version":"phase124-v1","state":"RETENTION_REGISTRY_HEALTHY","snapshot_count":1,"valid_snapshot_count":1,"expected_count":1,"history_state":"HISTORY_READY","history_reconciliation_fingerprint":"h","findings":[],"retention_registry_recommendation":"NO_RETENTION_REGISTRY_ACTION","read_only":True,"human_governed":True,"automatic_repair_performed":False,"execution_gate_closed":True,"execution_permitted":False,"execution_performed":False,"interpretation":"x","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None,"emergency_action":None}
    monitor=dict(p,monitor_fingerprint=fingerprint(p))
    review=review_retention_registry(monitor,actor_id="reviewer",role="coordinator",outcome="ACKNOWLEDGED",reviewed_at="2026-10-04T12:01:00+00:00")
    lifecycle=evaluate_retention_registry_review_lifecycle(review,evaluated_at="2026-10-04T12:02:00+00:00")
    return authorize_retention_registry_decision(lifecycle,actor_id="admin",role="admin",decision="AUTHORIZE_PRESERVATION",decided_at="2026-10-04T12:03:00+00:00",rationale="Preserve reviewed evidence.")


def test_empty_registry():
    r=build_retention_registry_authorization_registry_monitor([],expected_count=0,observed_at="2026-10-04T12:04:00+00:00")
    assert r["state"]=="NO_HISTORY"
    assert r["retention_registry_recommendation"]=="REVIEW_RETENTION_REGISTRY"
    assert validate_retention_registry_authorization_registry_monitor(r)==r


def test_healthy_registry_is_deterministic(tmp_path):
    registry=RetentionRegistryAuthorizationHistoryRegistry(tmp_path/"history.sqlite")
    snapshot=build_retention_registry_authorization_continuity([_decision()],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    registry.append(snapshot)
    a=monitor_registry(registry,observed_at="2026-10-04T12:05:00+00:00")
    b=monitor_registry(registry,observed_at="2026-10-04T12:05:00+00:00")
    assert a["state"]=="RETENTION_REGISTRY_HEALTHY"
    assert a["findings"]==[]
    assert a["monitor_fingerprint"]==b["monitor_fingerprint"]


def test_policy_mismatch():
    decision=_decision()
    snapshot=build_retention_registry_authorization_continuity([decision],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    record=dict(snapshot,registry_policy_version="wrong")
    r=build_retention_registry_authorization_registry_monitor([record],expected_count=1,observed_at="2026-10-04T12:05:00+00:00")
    assert r["state"]=="CONTROL_REQUIRED"
    assert any(x["code"]=="REGISTRY_POLICY_MISMATCH" for x in r["findings"])


def test_count_mismatch():
    r=build_retention_registry_authorization_registry_monitor([],expected_count=2,observed_at="2026-10-04T12:05:00+00:00")
    assert any(x["code"]=="REGISTRY_COUNT_MISMATCH" for x in r["findings"])


def test_sequence_gap():
    decision=_decision()
    first=build_retention_registry_authorization_continuity([decision],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    second=build_retention_registry_authorization_continuity([decision],captured_at="2026-10-04T12:05:00+00:00",sequence=3,previous_snapshot_fingerprint=first["snapshot_fingerprint"])
    r=build_retention_registry_authorization_registry_monitor([
        dict(first,registry_policy_version="phase132-v1"),
        dict(second,registry_policy_version="phase132-v1"),
    ],expected_count=2,observed_at="2026-10-04T12:06:00+00:00")
    assert r["state"]=="CONTROL_REQUIRED"
    assert any(x["code"]=="SEQUENCE_GAP" for x in r["findings"])


def test_execution_boundary_tamper():
    r=build_retention_registry_authorization_registry_monitor([],expected_count=0,observed_at="2026-10-04T12:05:00+00:00")
    r["execution_performed"]=True
    with pytest.raises(ValueError,match="MONITOR_FINGERPRINT_MISMATCH"):
        validate_retention_registry_authorization_registry_monitor(r)
