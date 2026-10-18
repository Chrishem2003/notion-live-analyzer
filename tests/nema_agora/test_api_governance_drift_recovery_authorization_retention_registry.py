import sqlite3
import tempfile
from pathlib import Path
from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_review import review_retention_health
from nema_agora.api_governance_drift_recovery_authorization_retention_lifecycle import evaluate_retention_review_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_decision import authorize_retention_decision
from nema_agora.api_governance_drift_recovery_authorization_retention_history import build_retention_authorization_continuity
from nema_agora.api_governance_drift_recovery_authorization_retention_registry import RetentionAuthorizationHistoryRegistry

def _decision():
    p={"policy_version":"phase117-v1","observed_at":"2026-10-04T12:00:00+00:00","registry_policy_version":"phase116-v1","state":"RETENTION_HEALTHY","snapshot_count":1,"valid_snapshot_count":1,"expected_count":1,"history_state":"HISTORY_READY","history_reconciliation_fingerprint":"synthetic-history","findings":[],"retention_recommendation":"NO_RETENTION_ACTION","read_only":True,"automatic_repair_performed":False,"execution_gate_closed":True,"interpretation":"AUTHORIZATION_RETENTION_INTEGRITY_MONITORING","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None}
    m=dict(p,monitor_fingerprint=fingerprint(p))
    r=review_retention_health(m,actor_id="reviewer",role="coordinator",outcome="ACKNOWLEDGED",reviewed_at="2026-10-04T12:01:00+00:00")
    l=evaluate_retention_review_lifecycle(r,evaluated_at="2026-10-04T12:02:00+00:00")
    return authorize_retention_decision(l,actor_id="admin",role="admin",decision="AUTHORIZE_PRESERVATION",decided_at="2026-10-04T12:03:00+00:00",rationale="Preserve evidence.")

def _snapshot(sequence=1, previous=None, captured="2026-10-04T12:04:00+00:00"):
    return build_retention_authorization_continuity([_decision()],captured_at=captured,sequence=sequence,previous_snapshot_fingerprint=previous)

def test_append_and_reconcile():
    with tempfile.TemporaryDirectory() as d:
        registry=RetentionAuthorizationHistoryRegistry(Path(d)/"retention.db")
        first=_snapshot()
        saved=registry.append(first)
        assert saved["registry_policy_version"]=="phase124-v1"
        assert registry.count()==1
        assert registry.reconcile_history()["state"]=="HISTORY_READY"
        assert registry.list()[0]["snapshot_fingerprint"]==first["snapshot_fingerprint"]

def test_requires_sequence_and_predecessor():
    with tempfile.TemporaryDirectory() as d:
        registry=RetentionAuthorizationHistoryRegistry(Path(d)/"retention.db")
        registry.append(_snapshot())
        second=_snapshot(2,"wrong","2026-10-04T12:05:00+00:00")
        try:
            registry.append(second)
        except ValueError as exc:
            assert str(exc)=="SNAPSHOT_PREDECESSOR_MISMATCH"
        else:
            raise AssertionError("predecessor mismatch must be rejected")

def test_rejects_duplicate_snapshot():
    with tempfile.TemporaryDirectory() as d:
        registry=RetentionAuthorizationHistoryRegistry(Path(d)/"retention.db")
        first=_snapshot()
        registry.append(first)
        try:
            registry.append(first)
        except ValueError as exc:
            assert str(exc)=="SNAPSHOT_HISTORY_CONFLICT"
        else:
            raise AssertionError("duplicate snapshot must be rejected")

def test_append_only():
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/"retention.db"
        registry=RetentionAuthorizationHistoryRegistry(path)
        registry.append(_snapshot())
        with sqlite3.connect(path) as db:
            try:
                db.execute("UPDATE retention_authorization_history SET captured_at='tampered'")
            except sqlite3.DatabaseError as exc:
                assert "append-only" in str(exc)
            else:
                raise AssertionError("updates must be blocked")
            try:
                db.execute("DELETE FROM retention_authorization_history")
            except sqlite3.DatabaseError as exc:
                assert "append-only" in str(exc)
            else:
                raise AssertionError("deletes must be blocked")

def test_limit_validation():
    with tempfile.TemporaryDirectory() as d:
        registry=RetentionAuthorizationHistoryRegistry(Path(d)/"retention.db")
        for bad in (0,501,True):
            try:
                registry.list(bad)
            except ValueError as exc:
                assert str(exc)=="INVALID_LIMIT"
            else:
                raise AssertionError("invalid limits must be rejected")
