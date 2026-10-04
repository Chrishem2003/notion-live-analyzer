"""Phase 155 tests — authorization decision continuity."""
from __future__ import annotations
import pytest
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_continuity_phase155 import (
    build_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity,
    reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity,
    validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_phase153 import authorize_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle

def decision():
    return authorize_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(
        {"policy_version":"phase152-v1","review_fingerprint":"r","monitor_fingerprint":"m","monitor_state":"CONTINUITY_HEALTHY","monitor_recommendation":"NO_CONTINUITY_ACTION","outcome":"ACKNOWLEDGED","state":"ACKNOWLEDGED","evaluated_at":"2026-10-04T12:00:00+00:00","human_governed":True,"automatic_repair_performed":False,"execution_gate_closed":True,"execution_permitted":False,"execution_performed":False,"environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None,"emergency_action":None,"lifecycle_fingerprint":"lifecycle-placeholder"},
        actor_id="admin", role="admin", decision="AUTHORIZE_PRESERVATION", decided_at="2026-10-04T13:00:00+00:00", rationale="Preserve evidence."
    )

def test_no_history_is_explicit():
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity([])
    assert result["state"] == "NO_HISTORY"
    assert validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity(result) == result

def test_first_snapshot_can_be_built_from_a_valid_decision():
    d = decision()
    snap = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity([d], captured_at="2026-10-04T14:00:00+00:00", sequence=1)
    assert snap["sequence"] == 1
    assert snap["decision_count"] == 1

def test_sequence_gap_requires_control():
    d = decision()
    first = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity([d], captured_at="2026-10-04T14:00:00+00:00", sequence=1)
    second = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity([d], captured_at="2026-10-04T15:00:00+00:00", sequence=2, previous_snapshot_fingerprint=first["snapshot_fingerprint"])
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity([first, second])
    assert result["state"] == "HISTORY_READY"

def test_tampered_snapshot_is_controlled():
    d = decision()
    snap = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity([d], captured_at="2026-10-04T14:00:00+00:00", sequence=1)
    bad = dict(snap, execution_performed=True)
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity([bad])
    assert result["state"] == "CONTROL_REQUIRED"
    assert "INVALID_SNAPSHOT" in result["findings"]
