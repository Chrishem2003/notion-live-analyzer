"""Tests for Phase 126 human review of retention-registry integrity."""
from __future__ import annotations

import pytest

from nema_agora.api_governance_drift_recovery_authorization_retention_registry_monitor import (
    build_retention_authorization_registry_monitor,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_review import (
    review_retention_registry,
    validate_retention_registry_review,
)

def _healthy():
    from nema_agora.api_audit_binding import fingerprint
    payload = {
        "policy_version": "phase125-v1",
        "observed_at": "2026-10-04T12:00:00+00:00",
        "registry_policy_version": "phase124-v1",
        "state": "RETENTION_REGISTRY_HEALTHY",
        "snapshot_count": 1,
        "valid_snapshot_count": 1,
        "expected_count": 1,
        "history_state": "HISTORY_READY",
        "history_reconciliation_fingerprint": "synthetic-history",
        "findings": [],
        "retention_registry_recommendation": "NO_RETENTION_REGISTRY_ACTION",
        "read_only": True,
        "human_governed": True,
        "automatic_repair_performed": False,
        "execution_gate_closed": True,
        "execution_permitted": False,
        "execution_performed": False,
        "interpretation": "RETENTION_AUTHORIZATION_REGISTRY_INTEGRITY_MONITORING",
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
        "emergency_action": None,
    }
    return dict(payload, monitor_fingerprint=fingerprint(payload))

def _control():
    return build_retention_authorization_registry_monitor(
        [{"registry_policy_version": "wrong-v1"}],
        expected_count=1, observed_at="2026-10-04T12:00:00+00:00"
    )

def test_healthy_registry_can_be_acknowledged():
    review = review_retention_registry(
        _healthy(), actor_id="reviewer-1", role="coordinator",
        outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:01:00+00:00",
        notes="registry state reviewed",
    )
    assert review["outcome"] == "ACKNOWLEDGED"
    assert validate_retention_registry_review(review)["review_fingerprint"] == review["review_fingerprint"]

def test_empty_registry_requires_review_not_acknowledgement():
    with pytest.raises(ValueError, match="ACKNOWLEDGED_REQUIRES_HEALTHY_REGISTRY"):
        review_retention_registry(
            _control(), actor_id="reviewer-1", role="coordinator",
            outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:01:00+00:00"
        )

def test_control_required_can_be_preserved_and_escalated():
    review = review_retention_registry(
        _control(), actor_id="admin-1", role="admin",
        outcome="PRESERVE_AND_ESCALATE", reviewed_at="2026-10-04T12:02:00+00:00",
        notes="preserve evidence and escalate for human investigation",
    )
    assert review["outcome"] == "PRESERVE_AND_ESCALATE"

def test_control_required_can_request_registry_review():
    review = review_retention_registry(
        _control(), actor_id="reviewer-1", role="coordinator",
        outcome="REVIEW_RETENTION_REGISTRY", reviewed_at="2026-10-04T12:03:00+00:00"
    )
    assert review["outcome"] == "REVIEW_RETENTION_REGISTRY"

def test_healthy_registry_cannot_be_marked_for_preservation_escalation():
    with pytest.raises(ValueError, match="PRESERVE_AND_ESCALATE_REQUIRES_CONTROL"):
        review_retention_registry(
            _healthy(), actor_id="reviewer-1", role="coordinator",
            outcome="PRESERVE_AND_ESCALATE", reviewed_at="2026-10-04T12:04:00+00:00"
        )

def test_tampered_execution_boundary_is_rejected():
    review = review_retention_registry(
        _healthy(), actor_id="reviewer-1", role="coordinator",
        outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:05:00+00:00"
    )
    tampered = dict(review, execution_permitted=True)
    with pytest.raises(ValueError, match="EXECUTION_GATE_VIOLATION"):
        validate_retention_registry_review(tampered)

def test_invalid_monitor_is_rejected():
    with pytest.raises(ValueError, match="INVALID_REGISTRY_MONITOR"):
        review_retention_registry(
            {"policy_version": "phase125-v1"}, actor_id="reviewer-1",
            role="coordinator", outcome="ACKNOWLEDGED",
            reviewed_at="2026-10-04T12:06:00+00:00"
        )
