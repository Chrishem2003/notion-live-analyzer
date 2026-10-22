"""Timezone-aware timestamp requirements for continuity monitoring and review."""
import pytest

from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_continuity_registry_monitor_phase157 import (
    build_lifecycle_decision_continuity_registry_monitor,
    validate_lifecycle_decision_continuity_registry_monitor,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_continuity_registry_review_phase158 import (
    review_lifecycle_decision_continuity_registry,
    validate_lifecycle_decision_continuity_registry_review,
)


def test_monitor_rejects_naive_observed_at_and_accepts_utc():
    with pytest.raises(ValueError, match="INVALID_OBSERVED_AT"):
        build_lifecycle_decision_continuity_registry_monitor([], observed_at="2026-10-22T10:00:00")
    report = build_lifecycle_decision_continuity_registry_monitor(
        [], observed_at="2026-10-22T10:00:00Z"
    )
    assert validate_lifecycle_decision_continuity_registry_monitor(report) == report


def test_review_rejects_naive_reviewed_at_and_accepts_utc():
    monitor = build_lifecycle_decision_continuity_registry_monitor(
        [], observed_at="2026-10-22T10:00:00Z"
    )
    with pytest.raises(ValueError, match="INVALID_REVIEW_TIME"):
        review_lifecycle_decision_continuity_registry(
            monitor, actor_id="reviewer-1", role="coordinator",
            outcome="REVIEW_CONTINUITY", reviewed_at="2026-10-22T10:01:00"
        )
    review = review_lifecycle_decision_continuity_registry(
        monitor, actor_id="reviewer-1", role="coordinator",
        outcome="REVIEW_CONTINUITY", reviewed_at="2026-10-22T10:01:00Z"
    )
    assert validate_lifecycle_decision_continuity_registry_review(review) == review


def test_monitor_validator_rejects_tampered_naive_timestamp():
    report = build_lifecycle_decision_continuity_registry_monitor(
        [], observed_at="2026-10-22T10:00:00Z"
    )
    report["observed_at"] = "2026-10-22T10:00:00"
    with pytest.raises(ValueError, match="INVALID_OBSERVED_AT"):
        validate_lifecycle_decision_continuity_registry_monitor(report)


def test_review_validator_rejects_tampered_naive_timestamp():
    monitor = build_lifecycle_decision_continuity_registry_monitor(
        [], observed_at="2026-10-22T10:00:00Z"
    )
    review = review_lifecycle_decision_continuity_registry(
        monitor, actor_id="reviewer-1", role="coordinator",
        outcome="REVIEW_CONTINUITY", reviewed_at="2026-10-22T10:01:00Z"
    )
    review["reviewed_at"] = "2026-10-22T10:01:00"
    with pytest.raises(ValueError, match="INVALID_REVIEW_TIME"):
        validate_lifecycle_decision_continuity_registry_review(review)
