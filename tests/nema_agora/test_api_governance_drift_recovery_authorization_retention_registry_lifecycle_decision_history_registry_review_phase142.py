"""Tests for Phase 142 human review of decision-history registry integrity."""
from __future__ import annotations

from copy import deepcopy

import pytest

from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_monitor_phase141 import (
    build_authorization_history_registry_decision_history_monitor,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_review_phase142 import (
    review_authorization_history_registry_decision_history,
    validate_authorization_history_registry_decision_history_review,
)


def _healthy():
    return build_authorization_history_registry_decision_history_monitor(
        [{
            "policy_version": "phase139-v1",
            "captured_at": "2026-10-04T12:11:00+00:00",
            "sequence": 1,
            "previous_snapshot_fingerprint": None,
            "decision_count": 0,
            "decisions": [],
            "human_governed": True,
            "execution_gate_closed": True,
            "execution_permitted": False,
            "execution_performed": False,
            "automatic_repair_performed": False,
            "environmental_conclusion": None,
            "regulatory_conclusion": None,
            "enforcement_action": None,
            "emergency_action": None,
            "snapshot_fingerprint": "placeholder",
            "registry_policy_version": "phase140-v1",
        }],
        expected_count=1,
        observed_at="2026-10-04T13:00:00+00:00",
    )


def _empty():
    return build_authorization_history_registry_decision_history_monitor(
        [], expected_count=0, observed_at="2026-10-04T13:00:00+00:00"
    )


def test_acknowledgement_requires_healthy_monitor():
    monitor = _healthy()
    review = review_authorization_history_registry_decision_history(
        monitor, actor_id="coordinator-142", role="coordinator",
        outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T13:05:00+00:00",
        notes="Evidence chain reviewed.",
    )
    assert review["monitor_fingerprint"] == monitor["monitor_fingerprint"]
    validate_authorization_history_registry_decision_history_review(review)


def test_empty_history_requires_explicit_review():
    review = review_authorization_history_registry_decision_history(
        _empty(), actor_id="coordinator-142", role="coordinator",
        outcome="REVIEW_AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY",
        reviewed_at="2026-10-04T13:05:00+00:00",
    )
    assert review["human_governed"] is True


def test_control_state_can_preserve_and_escalate():
    monitor = _empty()
    tampered = dict(monitor)
    tampered["state"] = "CONTROL_REQUIRED"
    from nema_agora.api_audit_binding import fingerprint
    payload = dict(tampered)
    payload.pop("monitor_fingerprint")
    tampered["monitor_fingerprint"] = fingerprint(payload)
    tampered["retention_registry_recommendation"] = "PRESERVE_AND_ESCALATE"
    payload = dict(tampered)
    payload.pop("monitor_fingerprint")
    tampered["monitor_fingerprint"] = fingerprint(payload)
    review = review_authorization_history_registry_decision_history(
        tampered, actor_id="admin-142", role="admin",
        outcome="PRESERVE_AND_ESCALATE", reviewed_at="2026-10-04T13:05:00+00:00",
    )
    assert review["outcome"] == "PRESERVE_AND_ESCALATE"


def test_unsafe_acknowledgement_is_blocked():
    with pytest.raises(ValueError, match="ACKNOWLEDGED_REQUIRES_HEALTHY_REGISTRY"):
        review_authorization_history_registry_decision_history(
            _empty(), actor_id="coordinator-142", role="coordinator",
            outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T13:05:00+00:00",
        )


def test_execution_tamper_is_rejected():
    review = review_authorization_history_registry_decision_history(
        _empty(), actor_id="coordinator-142", role="coordinator",
        outcome="REVIEW_AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY",
        reviewed_at="2026-10-04T13:05:00+00:00",
    )
    tampered = deepcopy(review)
    tampered["execution_performed"] = True
    with pytest.raises(ValueError, match="EXECUTION_GATE_VIOLATION"):
        validate_authorization_history_registry_decision_history_review(tampered)
