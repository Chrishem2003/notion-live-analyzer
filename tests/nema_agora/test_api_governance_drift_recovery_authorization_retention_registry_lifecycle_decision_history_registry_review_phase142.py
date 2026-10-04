"""Tests for Phase 142 human review of decision-history registry integrity."""
from __future__ import annotations

from copy import deepcopy

import pytest

from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_phase139 import (
    build_authorization_history_registry_decision_continuity,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_monitor_phase141 import (
    build_authorization_history_registry_decision_history_monitor,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_review_phase142 import (
    review_authorization_history_registry_decision_history,
    validate_authorization_history_registry_decision_history_review,
)


def _healthy():
    snapshot = build_authorization_history_registry_decision_continuity(
        [],
        captured_at="2026-10-04T12:11:00+00:00",
        sequence=1,
    )
    return build_authorization_history_registry_decision_history_monitor(
        [dict(snapshot, registry_policy_version="phase140-v1")],
        expected_count=1,
        observed_at="2026-10-04T13:00:00+00:00",
    )


def _empty():
    return build_authorization_history_registry_decision_history_monitor(
        [], expected_count=0, observed_at="2026-10-04T13:00:00+00:00"
    )


def _control_required():
    report = _empty()
    report["state"] = "CONTROL_REQUIRED"
    report["retention_registry_recommendation"] = "PRESERVE_AND_ESCALATE"
    from nema_agora.api_audit_binding import fingerprint
    payload = dict(report)
    payload.pop("monitor_fingerprint")
    report["monitor_fingerprint"] = fingerprint(payload)
    return report


def test_acknowledgement_requires_healthy_monitor():
    monitor = _healthy()
    assert monitor["state"] == "RETENTION_REGISTRY_HEALTHY"
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
    review = review_authorization_history_registry_decision_history(
        _control_required(), actor_id="admin-142", role="admin",
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
