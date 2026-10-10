"""Tests for Phase 145 lifecycle authorization decisions."""
from __future__ import annotations
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_monitor_phase141 import build_authorization_history_registry_decision_history_monitor
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_review_phase142 import review_authorization_history_registry_decision_history
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_review_reconciliation_phase143 import reconcile_authorization_history_registry_decision_history_reviews
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_review_lifecycle_phase144 import evaluate_authorization_history_registry_decision_history_review_lifecycle
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_phase145 import (
    authorize_authorization_history_registry_decision_history_lifecycle,
    validate_authorization_history_registry_decision_history_lifecycle_decision,
)

def _monitor():
    return build_authorization_history_registry_decision_history_monitor([], expected_count=0, observed_at="2026-10-04T13:00:00+00:00")

def _review(outcome="REVIEW_AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY"):
    return review_authorization_history_registry_decision_history(_monitor(), actor_id="coordinator-145", role="coordinator", outcome=outcome, reviewed_at="2026-10-04T13:05:00+00:00")

def _lifecycle(outcome="REVIEW_AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY"):
    return evaluate_authorization_history_registry_decision_history_review_lifecycle(_review(outcome), evaluated_at="2026-10-04T13:10:00+00:00")

def test_authorize_review_for_deferred():
    decision = authorize_authorization_history_registry_decision_history_lifecycle(
        _lifecycle(), actor_id="coordinator-145", role="coordinator",
        decision="AUTHORIZE_REVIEW", decided_at="2026-10-04T13:15:00+00:00",
        rationale="Human review is required before preservation.",
    )
    assert decision["human_authorized"] is True
    assert decision["execution_permitted"] is False
    validate_authorization_history_registry_decision_history_lifecycle_decision(decision)

def test_preservation_allowed_for_deferred():
    decision = authorize_authorization_history_registry_decision_history_lifecycle(
        _lifecycle(), actor_id="coordinator-145", role="coordinator",
        decision="AUTHORIZE_PRESERVATION", decided_at="2026-10-04T13:15:00+00:00",
        rationale="Preserve the evidence record for review continuity.",
    )
    assert decision["decision"] == "AUTHORIZE_PRESERVATION"

def test_escalation_requires_escalated_lifecycle():
    try:
        authorize_authorization_history_registry_decision_history_lifecycle(
            _lifecycle(), actor_id="coordinator-145", role="coordinator",
            decision="AUTHORIZE_ESCALATION", decided_at="2026-10-04T13:15:00+00:00",
            rationale="Escalation requested.",
        )
    except ValueError as exc:
        assert str(exc) == "DECISION_STATE_MISMATCH"
    else:
        raise AssertionError("expected lifecycle decision boundary")

def test_tampered_decision_rejected():
    decision = authorize_authorization_history_registry_decision_history_lifecycle(
        _lifecycle(), actor_id="coordinator-145", role="coordinator",
        decision="AUTHORIZE_REVIEW", decided_at="2026-10-04T13:15:00+00:00",
        rationale="Review required.",
    )
    decision["execution_permitted"] = True
    from nema_agora.api_audit_binding import fingerprint
    payload = dict(decision)
    payload.pop("decision_fingerprint")
    decision["decision_fingerprint"] = fingerprint(payload)
    try:
        validate_authorization_history_registry_decision_history_lifecycle_decision(decision)
    except ValueError as exc:
        assert str(exc) == "EXECUTION_FORBIDDEN"
    else:
        raise AssertionError("expected execution rejection")
