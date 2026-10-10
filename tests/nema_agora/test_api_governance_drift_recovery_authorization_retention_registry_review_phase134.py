import pytest

from nema_agora.api_governance_drift_recovery_authorization_retention_registry_registry_monitor import (
    build_retention_registry_authorization_registry_monitor,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_review_phase134 import (
    review_authorization_history_registry,
    validate_authorization_history_registry_review,
)


def test_no_history_cannot_be_acknowledged():
    p = build_retention_registry_authorization_registry_monitor(
        [], expected_count=0, observed_at="2026-10-04T12:00:00+00:00"
    )
    with pytest.raises(ValueError, match="ACKNOWLEDGED_REQUIRES_HEALTHY_REGISTRY"):
        review_authorization_history_registry(
            p, actor_id="reviewer", role="coordinator", outcome="ACKNOWLEDGED",
            reviewed_at="2026-10-04T12:02:00+00:00",
        )


def test_review_outcome_for_control_required():
    p = build_retention_registry_authorization_registry_monitor(
        [], expected_count=1, observed_at="2026-10-04T12:00:00+00:00"
    )
    r = review_authorization_history_registry(
        p, actor_id="reviewer", role="coordinator",
        outcome="REVIEW_AUTHORIZATION_HISTORY_REGISTRY",
        reviewed_at="2026-10-04T12:02:00+00:00",
    )
    assert r["monitor_fingerprint"] == p["monitor_fingerprint"]
    assert validate_authorization_history_registry_review(r) == r


def test_preserve_and_escalate_requires_control():
    p = build_retention_registry_authorization_registry_monitor(
        [], expected_count=1, observed_at="2026-10-04T12:00:00+00:00"
    )
    r = review_authorization_history_registry(
        p, actor_id="admin", role="admin",
        outcome="PRESERVE_AND_ESCALATE",
        reviewed_at="2026-10-04T12:02:00+00:00",
    )
    assert r["outcome"] == "PRESERVE_AND_ESCALATE"


def test_execution_boundary_tamper():
    p = build_retention_registry_authorization_registry_monitor(
        [], expected_count=1, observed_at="2026-10-04T12:00:00+00:00"
    )
    r = review_authorization_history_registry(
        p, actor_id="admin", role="admin", outcome="ESCALATED",
        reviewed_at="2026-10-04T12:02:00+00:00",
    )
    r["execution_performed"] = True
    with pytest.raises(ValueError, match="EXECUTION_GATE_VIOLATION"):
        validate_authorization_history_registry_review(r)


def test_fingerprint_is_deterministic():
    p = build_retention_registry_authorization_registry_monitor(
        [], expected_count=1, observed_at="2026-10-04T12:00:00+00:00"
    )
    a = review_authorization_history_registry(
        p, actor_id="reviewer", role="coordinator", outcome="ESCALATED",
        reviewed_at="2026-10-04T12:02:00+00:00", notes="Control review.",
    )
    b = review_authorization_history_registry(
        p, actor_id="reviewer", role="coordinator", outcome="ESCALATED",
        reviewed_at="2026-10-04T12:02:00+00:00", notes="Control review.",
    )
    assert a["review_fingerprint"] == b["review_fingerprint"]
