"""Tests for Phase 144 review lifecycle."""
from __future__ import annotations
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_monitor_phase141 import build_authorization_history_registry_decision_history_monitor
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_review_phase142 import review_authorization_history_registry_decision_history
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_review_reconciliation_phase143 import reconcile_authorization_history_registry_decision_history_reviews
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_review_lifecycle_phase144 import (
    build_authorization_history_registry_decision_history_review_lifecycle,
    evaluate_authorization_history_registry_decision_history_review_lifecycle,
    validate_authorization_history_registry_decision_history_review_lifecycle,
    validate_authorization_history_registry_decision_history_review_lifecycle_bundle,
)

def _monitor():
    return build_authorization_history_registry_decision_history_monitor([], expected_count=0, observed_at="2026-10-04T13:00:00+00:00")

def _review(outcome="REVIEW_AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY"):
    return review_authorization_history_registry_decision_history(
        _monitor(), actor_id="coordinator-144", role="coordinator", outcome=outcome,
        reviewed_at="2026-10-04T13:05:00+00:00",
    )

def _reconciliation(review):
    return reconcile_authorization_history_registry_decision_history_reviews([_monitor()], [review], expected_review_count=1)

def test_review_maps_to_deferred():
    lifecycle = evaluate_authorization_history_registry_decision_history_review_lifecycle(_review(), evaluated_at="2026-10-04T13:10:00+00:00")
    assert lifecycle["lifecycle_state"] == "DEFERRED"
    validate_authorization_history_registry_decision_history_review_lifecycle(lifecycle)

def test_escalation_maps_to_escalated():
    review = _review("ESCALATED")
    lifecycle = evaluate_authorization_history_registry_decision_history_review_lifecycle(review, evaluated_at="2026-10-04T13:10:00+00:00")
    assert lifecycle["lifecycle_state"] == "ESCALATED"

def test_reconciled_reviews_build_bundle():
    review = _review()
    rec = _reconciliation(review)
    bundle = build_authorization_history_registry_decision_history_review_lifecycle(rec, [review], evaluated_at="2026-10-04T13:10:00+00:00")
    assert bundle["lifecycle_count"] == 1
    assert bundle["execution_gate_closed"] is True
    validate_authorization_history_registry_decision_history_review_lifecycle_bundle(bundle)

def test_non_reconciled_blocks_bundle():
    review = _review()
    rec = _reconciliation(review)
    rec["state"] = "CONTROL_REQUIRED"
    from nema_agora.api_audit_binding import fingerprint
    payload = dict(rec)
    payload.pop("reconciliation_fingerprint")
    rec["reconciliation_fingerprint"] = fingerprint(payload)
    try:
        build_authorization_history_registry_decision_history_review_lifecycle(rec, [review], evaluated_at="2026-10-04T13:10:00+00:00")
    except ValueError as exc:
        assert str(exc) == "RECONCILIATION_MUST_BE_RECONCILED"
    else:
        raise AssertionError("expected reconciliation gate")

def test_tampered_lifecycle_rejected():
    lifecycle = evaluate_authorization_history_registry_decision_history_review_lifecycle(_review(), evaluated_at="2026-10-04T13:10:00+00:00")
    lifecycle["execution_performed"] = True
    from nema_agora.api_audit_binding import fingerprint
    payload = dict(lifecycle)
    payload.pop("lifecycle_fingerprint")
    lifecycle["lifecycle_fingerprint"] = fingerprint(payload)
    try:
        validate_authorization_history_registry_decision_history_review_lifecycle(lifecycle)
    except ValueError as exc:
        assert str(exc) == "INVALID_EXECUTION_CONTROLS"
    else:
        raise AssertionError("expected execution-control rejection")
