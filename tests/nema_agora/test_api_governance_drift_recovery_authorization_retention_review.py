import pytest

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_monitor import build_authorization_retention_monitor
from nema_agora.api_governance_drift_recovery_authorization_retention_review import (
    review_retention_health,
    validate_retention_review,
)


def _monitor(state="RETENTION_HEALTHY", recommendation="NO_RETENTION_ACTION"):
    payload = {
        "policy_version": "phase117-v1",
        "observed_at": "2026-10-04T12:00:00+00:00",
        "registry_policy_version": "phase116-v1",
        "state": state,
        "snapshot_count": 1 if state == "RETENTION_HEALTHY" else 0,
        "valid_snapshot_count": 1 if state == "RETENTION_HEALTHY" else 0,
        "expected_count": 1 if state == "RETENTION_HEALTHY" else 0,
        "history_state": "HISTORY_READY" if state == "RETENTION_HEALTHY" else "NO_HISTORY",
        "history_reconciliation_fingerprint": "synthetic-history",
        "findings": [] if state == "RETENTION_HEALTHY" else [{"code": "CONTROL_REQUIRED"}],
        "retention_recommendation": recommendation,
        "read_only": True,
        "automatic_repair_performed": False,
        "execution_gate_closed": True,
        "interpretation": "AUTHORIZATION_RETENTION_INTEGRITY_MONITORING",
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
    }
    return dict(payload, monitor_fingerprint=fingerprint(payload))


def test_acknowledge_healthy_monitor():
    review = review_retention_health(
        _monitor(),
        actor_id="reviewer",
        role="coordinator",
        outcome="ACKNOWLEDGED",
        reviewed_at="2026-10-04T12:01:00+00:00",
    )
    assert review["outcome"] == "ACKNOWLEDGED"
    assert review["human_governed"] is True
    assert review["execution_gate_closed"] is True
    assert validate_retention_review(review)["review_fingerprint"] == review["review_fingerprint"]


def test_control_state_requires_preservation_or_review():
    monitor = _monitor("CONTROL_REQUIRED", "PRESERVE_AND_ESCALATE")
    with pytest.raises(ValueError, match="ACKNOWLEDGED_REQUIRES_HEALTHY_RETENTION"):
        review_retention_health(
            monitor, actor_id="reviewer", role="coordinator",
            outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:01:00+00:00"
        )
    review = review_retention_health(
        monitor, actor_id="reviewer", role="coordinator",
        outcome="PRESERVE_AND_ESCALATE", reviewed_at="2026-10-04T12:01:00+00:00"
    )
    assert review["outcome"] == "PRESERVE_AND_ESCALATE"


def test_no_history_can_be_reviewed():
    monitor = _monitor("NO_HISTORY", "REVIEW_RETENTION")
    review = review_retention_health(
        monitor, actor_id="admin", role="admin",
        outcome="REVIEW_RETENTION", reviewed_at="2026-10-04T12:01:00+00:00",
        notes="Retention history has not been established yet.",
    )
    assert review["monitor_state"] == "NO_HISTORY"


def test_tampered_monitor_is_rejected():
    monitor = _monitor()
    monitor["state"] = "CONTROL_REQUIRED"
    with pytest.raises(ValueError, match="RETENTION_MONITOR_FINGERPRINT_MISMATCH"):
        review_retention_health(
            monitor, actor_id="reviewer", role="coordinator",
            outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:01:00+00:00"
        )


def test_review_fingerprint_is_deterministic():
    monitor = _monitor()
    a = review_retention_health(
        monitor, actor_id="reviewer", role="coordinator",
        outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:01:00+00:00"
    )
    b = review_retention_health(
        monitor, actor_id="reviewer", role="coordinator",
        outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:01:00+00:00"
    )
    assert a["review_fingerprint"] == b["review_fingerprint"]
