"""Phase 150 tests — human review of continuity integrity evidence."""

from __future__ import annotations

import pytest

from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_phase147 import (
    build_authorization_history_registry_decision_history_lifecycle_decision_continuity,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_monitor_phase149 import (
    build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_phase150 import (
    review_authorization_history_registry_decision_history_lifecycle_decision_continuity,
    validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review,
)


def monitor(state_case: str):
    if state_case == "healthy":
        snapshot = build_authorization_history_registry_decision_history_lifecycle_decision_continuity(
            [], captured_at="2026-10-04T09:00:00+00:00", sequence=1
        )
        return build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(
            [snapshot], expected_count=1, observed_at="2026-10-04T10:00:00+00:00"
        )
    if state_case == "control":
        snapshot = build_authorization_history_registry_decision_history_lifecycle_decision_continuity(
            [], captured_at="2026-10-04T09:00:00+00:00", sequence=1
        )
        tampered = dict(snapshot, snapshot_fingerprint="tampered")
        return build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(
            [tampered], observed_at="2026-10-04T10:00:00+00:00"
        )
    return build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(
        [], observed_at="2026-10-04T10:00:00+00:00"
    )


def test_healthy_continuity_can_be_acknowledged():
    review = review_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        monitor("healthy"), actor_id="reviewer-1", role="coordinator",
        outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T11:00:00+00:00"
    )
    assert review["outcome"] == "ACKNOWLEDGED"
    assert validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review(review) == review


def test_no_history_requires_explicit_review_or_escalation():
    report = monitor("no_history")
    review = review_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        report, actor_id="reviewer-1", role="admin", outcome="REVIEW_CONTINUITY",
        reviewed_at="2026-10-04T11:00:00+00:00", notes="Continuity history is not yet established."
    )
    assert review["outcome"] == "REVIEW_CONTINUITY"


def test_control_required_can_be_preserved_and_escalated():
    review = review_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        monitor("control"), actor_id="reviewer-1", role="admin",
        outcome="PRESERVE_AND_ESCALATE", reviewed_at="2026-10-04T11:00:00+00:00"
    )
    assert review["outcome"] == "PRESERVE_AND_ESCALATE"


def test_unsafe_acknowledgement_is_blocked():
    with pytest.raises(ValueError, match="ACKNOWLEDGED_REQUIRES_HEALTHY_CONTINUITY"):
        review_authorization_history_registry_decision_history_lifecycle_decision_continuity(
            monitor("control"), actor_id="reviewer-1", role="coordinator",
            outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T11:00:00+00:00"
        )


def test_monitor_binding_tamper_is_rejected():
    report = monitor("healthy")
    review = review_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        report, actor_id="reviewer-1", role="coordinator",
        outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T11:00:00+00:00"
    )
    tampered = dict(review, monitor_fingerprint="wrong")
    with pytest.raises(ValueError, match="REVIEW_FINGERPRINT_MISMATCH"):
        validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review(tampered)


def test_execution_tamper_is_rejected():
    report = monitor("healthy")
    review = review_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        report, actor_id="reviewer-1", role="coordinator",
        outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T11:00:00+00:00"
    )
    tampered = dict(review, execution_performed=True)
    with pytest.raises(ValueError, match="REVIEW_FINGERPRINT_MISMATCH"):
        validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review(tampered)
