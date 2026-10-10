import sqlite3

import pytest

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_decision import (
    authorize_retention_registry_decision,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_history import (
    build_retention_registry_authorization_continuity,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle import (
    evaluate_retention_registry_review_lifecycle,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_review import (
    review_retention_registry,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_registry import (
    RetentionRegistryAuthorizationHistoryRegistry,
)


def _decision():
    p={"policy_version":"phase125-v1","observed_at":"2026-10-04T12:00:00+00:00","registry_policy_version":"phase124-v1","state":"RETENTION_REGISTRY_HEALTHY","snapshot_count":1,"valid_snapshot_count":1,"expected_count":1,"history_state":"HISTORY_READY","history_reconciliation_fingerprint":"h","findings":[],"retention_registry_recommendation":"NO_RETENTION_REGISTRY_ACTION","read_only":True,"human_governed":True,"automatic_repair_performed":False,"execution_gate_closed":True,"execution_permitted":False,"execution_performed":False,"interpretation":"x","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None,"emergency_action":None}
    monitor=dict(p,monitor_fingerprint=fingerprint(p))
    review=review_retention_registry(monitor,actor_id="reviewer",role="coordinator",outcome="ACKNOWLEDGED",reviewed_at="2026-10-04T12:01:00+00:00")
    lifecycle=evaluate_retention_registry_review_lifecycle(review,evaluated_at="2026-10-04T12:02:00+00:00")
    return authorize_retention_registry_decision(lifecycle,actor_id="admin",role="admin",decision="AUTHORIZE_PRESERVATION",decided_at="2026-10-04T12:03:00+00:00",rationale="Preserve reviewed evidence.")


def test_append_list_reconcile_and_count(tmp_path):
    registry=RetentionRegistryAuthorizationHistoryRegistry(tmp_path/"history.sqlite")
    snapshot=build_retention_registry_authorization_continuity([_decision()],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    stored=registry.append(snapshot)
    assert stored["registry_policy_version"]=="phase132-v1"
    assert registry.count()==1
    assert registry.list()==[dict(snapshot,registry_policy_version="phase132-v1")]
    assert registry.reconcile_history()["state"]=="HISTORY_READY"


def test_requires_first_sequence(tmp_path):
    registry=RetentionRegistryAuthorizationHistoryRegistry(tmp_path/"history.sqlite")
    snapshot=build_retention_registry_authorization_continuity([_decision()],captured_at="2026-10-04T12:04:00+00:00",sequence=2)
    with pytest.raises(ValueError,match="FIRST_SNAPSHOT_SEQUENCE_REQUIRED"):
        registry.append(snapshot)


def test_requires_exact_next_and_predecessor(tmp_path):
    registry=RetentionRegistryAuthorizationHistoryRegistry(tmp_path/"history.sqlite")
    first=build_retention_registry_authorization_continuity([_decision()],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    registry.append(first)
    gap=build_retention_registry_authorization_continuity([_decision()],captured_at="2026-10-04T12:05:00+00:00",sequence=3,previous_snapshot_fingerprint=first["snapshot_fingerprint"])
    with pytest.raises(ValueError,match="SNAPSHOT_SEQUENCE_NOT_NEXT"):
        registry.append(gap)
    wrong=build_retention_registry_authorization_continuity([_decision()],captured_at="2026-10-04T12:05:00+00:00",sequence=2,previous_snapshot_fingerprint="wrong")
    with pytest.raises(ValueError,match="SNAPSHOT_PREDECESSOR_MISMATCH"):
        registry.append(wrong)


def test_duplicate_snapshot_rejected(tmp_path):
    registry=RetentionRegistryAuthorizationHistoryRegistry(tmp_path/"history.sqlite")
    snapshot=build_retention_registry_authorization_continuity([_decision()],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    registry.append(snapshot)
    with pytest.raises(ValueError,match="SNAPSHOT_HISTORY_CONFLICT"):
        registry.append(snapshot)


def test_update_delete_are_blocked(tmp_path):
    registry=RetentionRegistryAuthorizationHistoryRegistry(tmp_path/"history.sqlite")
    snapshot=build_retention_registry_authorization_continuity([_decision()],captured_at="2026-10-04T12:04:00+00:00",sequence=1)
    registry.append(snapshot)
    with pytest.raises(sqlite3.IntegrityError,match="append-only"):
        with registry._connect() as db:
            db.execute("UPDATE retention_registry_authorization_history SET sequence=9")
    with pytest.raises(sqlite3.IntegrityError,match="append-only"):
        with registry._connect() as db:
            db.execute("DELETE FROM retention_registry_authorization_history")


def test_invalid_limits(tmp_path):
    registry=RetentionRegistryAuthorizationHistoryRegistry(tmp_path/"history.sqlite")
    with pytest.raises(ValueError,match="INVALID_LIMIT"):
        registry.list(0)
    with pytest.raises(ValueError,match="INVALID_LIMIT"):
        registry.list(501)
