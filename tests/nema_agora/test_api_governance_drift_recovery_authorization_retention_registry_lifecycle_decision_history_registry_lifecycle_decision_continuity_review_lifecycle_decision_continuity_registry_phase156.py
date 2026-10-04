"""Phase 156 tests — append-only continuity registry."""
from __future__ import annotations
import sqlite3
import pytest
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_phase147 import build_authorization_history_registry_decision_history_lifecycle_decision_continuity as build_phase147
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_monitor_phase149 import build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_phase150 import review_authorization_history_registry_decision_history_lifecycle_decision_continuity
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_phase152 import evaluate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_phase153 import authorize_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_continuity_phase155 import build_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_continuity_registry_phase156 import LifecycleDecisionContinuityRegistry

def snapshot():
    s = build_phase147([], captured_at="2026-10-04T09:00:00+00:00", sequence=1)
    m = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor([s], expected_count=1, observed_at="2026-10-04T10:00:00+00:00")
    r = review_authorization_history_registry_decision_history_lifecycle_decision_continuity(m, actor_id="reviewer", role="coordinator", outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T11:00:00+00:00")
    l = evaluate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(r, evaluated_at="2026-10-04T12:00:00+00:00")
    d = authorize_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(l, actor_id="admin", role="admin", decision="AUTHORIZE_PRESERVATION", decided_at="2026-10-04T13:00:00+00:00", rationale="Preserve evidence.")
    return build_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity([d], captured_at="2026-10-04T14:00:00+00:00", sequence=1)

def test_append_list_count_validate(tmp_path):
    registry = LifecycleDecisionContinuityRegistry(tmp_path / "registry.sqlite")
    s = snapshot()
    assert registry.append(s)["snapshot_fingerprint"] == s["snapshot_fingerprint"]
    assert registry.count() == 1
    assert registry.list() == [s]
    assert registry.validate() == [s]

def test_append_only_blocks_update_and_delete(tmp_path):
    registry = LifecycleDecisionContinuityRegistry(tmp_path / "registry.sqlite")
    registry.append(snapshot())
    with pytest.raises(sqlite3.IntegrityError):
        with registry._connect() as conn:
            conn.execute(f"UPDATE lifecycle_decision_continuity_review_lifecycle_decision_continuity SET sequence=9 WHERE sequence=1")
    with pytest.raises(sqlite3.IntegrityError):
        with registry._connect() as conn:
            conn.execute(f"DELETE FROM lifecycle_decision_continuity_review_lifecycle_decision_continuity WHERE sequence=1")
