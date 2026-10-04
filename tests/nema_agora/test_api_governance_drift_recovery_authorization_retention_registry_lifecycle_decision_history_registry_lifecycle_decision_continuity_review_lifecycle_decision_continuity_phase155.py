"""Phase 155 tests — authorization decision continuity."""
from __future__ import annotations
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_phase147 import build_authorization_history_registry_decision_history_lifecycle_decision_continuity as build_phase147
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_monitor_phase149 import build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_phase150 import review_authorization_history_registry_decision_history_lifecycle_decision_continuity
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_phase152 import evaluate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_phase153 import authorize_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_continuity_phase155 import build_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity, reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity, validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity

def decision():
    snapshot = build_phase147([], captured_at="2026-10-04T09:00:00+00:00", sequence=1)
    monitor = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor([snapshot], expected_count=1, observed_at="2026-10-04T10:00:00+00:00")
    review = review_authorization_history_registry_decision_history_lifecycle_decision_continuity(monitor, actor_id="reviewer", role="coordinator", outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T11:00:00+00:00")
    lifecycle = evaluate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(review, evaluated_at="2026-10-04T12:00:00+00:00")
    return authorize_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(lifecycle, actor_id="admin", role="admin", decision="AUTHORIZE_PRESERVATION", decided_at="2026-10-04T13:00:00+00:00", rationale="Preserve evidence.")

def test_no_history_is_explicit():
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity([])
    assert result["state"] == "NO_HISTORY"
    assert validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity(result) == result

def test_first_snapshot_can_be_built_from_a_valid_decision():
    snap = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity([decision()], captured_at="2026-10-04T14:00:00+00:00", sequence=1)
    assert snap["sequence"] == 1 and snap["decision_count"] == 1

def test_chained_snapshot_is_continuous():
    d = decision()
    first = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity([d], captured_at="2026-10-04T14:00:00+00:00", sequence=1)
    second = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity([d], captured_at="2026-10-04T15:00:00+00:00", sequence=2, previous_snapshot_fingerprint=first["snapshot_fingerprint"])
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity([first, second])
    assert result["state"] == "HISTORY_READY"

def test_tampered_snapshot_is_controlled():
    snap = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity([decision()], captured_at="2026-10-04T14:00:00+00:00", sequence=1)
    bad = dict(snap, execution_performed=True)
    result = reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity([bad])
    assert result["state"] == "CONTROL_REQUIRED" and "INVALID_SNAPSHOT" in result["findings"]
