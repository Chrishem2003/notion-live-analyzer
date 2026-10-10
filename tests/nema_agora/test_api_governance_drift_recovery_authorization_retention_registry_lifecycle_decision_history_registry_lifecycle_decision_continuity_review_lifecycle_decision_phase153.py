"""Phase 153 tests — human authorization boundary for continuity review lifecycle."""
from __future__ import annotations
import pytest
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_phase147 import build_authorization_history_registry_decision_history_lifecycle_decision_continuity
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_monitor_phase149 import build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_phase150 import review_authorization_history_registry_decision_history_lifecycle_decision_continuity
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_phase152 import evaluate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_phase153 import (
    authorize_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle,
    validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision,
)

def lifecycle(outcome="ACKNOWLEDGED"):
    if outcome == "REVIEW_CONTINUITY":
        monitor = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor([], observed_at="2026-10-04T10:00:00+00:00")
    else:
        snapshot = build_authorization_history_registry_decision_history_lifecycle_decision_continuity([], captured_at="2026-10-04T09:00:00+00:00", sequence=1)
        monitor = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor([snapshot], expected_count=1, observed_at="2026-10-04T10:00:00+00:00")
    review = review_authorization_history_registry_decision_history_lifecycle_decision_continuity(monitor, actor_id="reviewer-1", role="coordinator", outcome=outcome, reviewed_at="2026-10-04T11:00:00+00:00")
    return evaluate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(review, evaluated_at="2026-10-04T12:00:00+00:00")

def test_acknowledged_lifecycle_allows_preservation():
    decision = authorize_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(
        lifecycle(), actor_id="admin-1", role="admin", decision="AUTHORIZE_PRESERVATION",
        decided_at="2026-10-04T13:00:00+00:00", rationale="Preserve the reviewed continuity evidence."
    )
    assert decision["decision"] == "AUTHORIZE_PRESERVATION"
    assert validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision(decision) == decision

def test_deferred_lifecycle_allows_review_authorization():
    decision = authorize_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(
        lifecycle("REVIEW_CONTINUITY"), actor_id="coordinator-1", role="coordinator", decision="AUTHORIZE_REVIEW",
        decided_at="2026-10-04T13:00:00+00:00", rationale="Authorize a human continuity review."
    )
    assert decision["decision"] == "AUTHORIZE_REVIEW"

def test_wrong_state_is_blocked():
    with pytest.raises(ValueError, match="DECISION_NOT_ALLOWED_FOR_LIFECYCLE_STATE"):
        authorize_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(
            lifecycle(), actor_id="admin-1", role="admin", decision="AUTHORIZE_REVIEW",
            decided_at="2026-10-04T13:00:00+00:00", rationale="Not permitted from acknowledged state."
        )

def test_tampered_decision_is_rejected():
    decision = authorize_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(
        lifecycle(), actor_id="admin-1", role="admin", decision="AUTHORIZE_PRESERVATION",
        decided_at="2026-10-04T13:00:00+00:00", rationale="Preserve evidence."
    )
    tampered = dict(decision, lifecycle_fingerprint="wrong")
    with pytest.raises(ValueError, match="EXECUTION_GATE_VIOLATION"):
        validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision(tampered)

def test_execution_tamper_is_rejected():
    decision = authorize_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(
        lifecycle(), actor_id="admin-1", role="admin", decision="AUTHORIZE_PRESERVATION",
        decided_at="2026-10-04T13:00:00+00:00", rationale="Preserve evidence."
    )
    tampered = dict(decision, execution_performed=True)
    with pytest.raises(ValueError, match="DECISION_FINGERPRINT_MISMATCH"):
        validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision(tampered)
