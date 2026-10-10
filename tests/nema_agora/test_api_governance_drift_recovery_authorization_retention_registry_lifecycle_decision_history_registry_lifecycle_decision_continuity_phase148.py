"""Tests for Phase 148 persistent continuity registry."""
from pathlib import Path
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_phase147 import build_authorization_history_registry_decision_history_lifecycle_decision_continuity
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_phase148 import AuthorizationHistoryRegistryDecisionHistoryLifecycleDecisionContinuityRegistry
def _snapshot(seq,prev=None):
    return build_authorization_history_registry_decision_history_lifecycle_decision_continuity([],captured_at=f"2026-10-04T14:{seq:02d}:00+00:00",sequence=seq,previous_snapshot_fingerprint=prev)
def test_append_list_count_and_validate(tmp_path:Path):
    registry=AuthorizationHistoryRegistryDecisionHistoryLifecycleDecisionContinuityRegistry(tmp_path/"history.db")
    first=_snapshot(1)
    registry.append(first)
    assert registry.count()==1
    assert registry.list()[0]["snapshot_fingerprint"]==first["snapshot_fingerprint"]
    assert len(registry.validate())==1
def test_append_second_snapshot(tmp_path:Path):
    registry=AuthorizationHistoryRegistryDecisionHistoryLifecycleDecisionContinuityRegistry(tmp_path/"history.db")
    first=_snapshot(1); second=_snapshot(2,first["snapshot_fingerprint"])
    registry.append(first); registry.append(second)
    assert [x["sequence"] for x in registry.list()]==[1,2]
def test_duplicate_sequence_rejected(tmp_path:Path):
    registry=AuthorizationHistoryRegistryDecisionHistoryLifecycleDecisionContinuityRegistry(tmp_path/"history.db")
    registry.append(_snapshot(1))
    try: registry.append(_snapshot(1))
    except Exception: assert True
    else: assert False
def test_update_delete_blocked(tmp_path:Path):
    registry=AuthorizationHistoryRegistryDecisionHistoryLifecycleDecisionContinuityRegistry(tmp_path/"history.db")
    registry.append(_snapshot(1))
    import sqlite3
    with sqlite3.connect(tmp_path/"history.db") as db:
        try: db.execute("UPDATE authorization_history_registry_decision_history_lifecycle_decision_continuity SET sequence=2 WHERE sequence=1")
        except sqlite3.DatabaseError: pass
        else: assert False
        try: db.execute("DELETE FROM authorization_history_registry_decision_history_lifecycle_decision_continuity WHERE sequence=1")
        except sqlite3.DatabaseError: pass
        else: assert False
