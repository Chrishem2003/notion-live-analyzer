"""Tests for Phase 125 retention-authorization registry monitoring."""
from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path

import pytest

from nema_agora.api_governance_drift_recovery_authorization_retention_registry import (
    RetentionAuthorizationHistoryRegistry,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_monitor import (
    build_retention_authorization_registry_monitor,
    monitor_registry,
    validate_retention_registry_monitor,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_history import (
    build_retention_authorization_continuity,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_decision import (
    authorize_retention_decision,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_lifecycle import (
    evaluate_retention_review_lifecycle,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_review import (
    review_retention_health,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_monitor import (
    build_authorization_retention_monitor,
)

def _decision():
    monitor = build_authorization_retention_monitor([], expected_count=0, observed_at="2026-10-04T10:00:00+00:00")
    review = review_retention_health(
        monitor, actor_id="reviewer-1", role="coordinator", outcome="ACKNOWLEDGED",
        reviewed_at="2026-10-04T10:01:00+00:00", notes="healthy retention evidence"
    )
    lifecycle = evaluate_retention_review_lifecycle(review, evaluated_at="2026-10-04T10:02:00+00:00")
    return authorize_retention_decision(
        lifecycle, actor_id="reviewer-1", role="coordinator",
        decision="AUTHORIZE_PRESERVATION", decided_at="2026-10-04T10:03:00+00:00",
        rationale="preserve the healthy evidence chain"
    )

def _snapshot():
    return build_retention_authorization_continuity(
        [_decision()], captured_at="2026-10-04T10:04:00+00:00", sequence=1
    )

def test_empty_registry_requests_review():
    report = build_retention_authorization_registry_monitor([], expected_count=0, observed_at="2026-10-04T11:00:00+00:00")
    assert report["state"] == "NO_HISTORY"
    assert report["retention_registry_recommendation"] == "REVIEW_RETENTION_REGISTRY"
    assert validate_retention_registry_monitor(report)["monitor_fingerprint"] == report["monitor_fingerprint"]

def test_healthy_registry_is_deterministic():
    record = dict(_snapshot(), registry_policy_version="phase124-v1")
    a = build_retention_authorization_registry_monitor([record], expected_count=1, observed_at="2026-10-04T11:00:00+00:00")
    b = build_retention_authorization_registry_monitor([record], expected_count=1, observed_at="2026-10-04T11:00:00+00:00")
    assert a["state"] == "RETENTION_REGISTRY_HEALTHY"
    assert a["monitor_fingerprint"] == b["monitor_fingerprint"]

def test_registry_policy_mismatch_requires_control():
    record = dict(_snapshot(), registry_policy_version="wrong-v1")
    report = build_retention_authorization_registry_monitor([record], expected_count=1, observed_at="2026-10-04T11:00:00+00:00")
    assert report["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "REGISTRY_POLICY_MISMATCH" for x in report["findings"])

def test_count_mismatch_requires_control():
    record = dict(_snapshot(), registry_policy_version="phase124-v1")
    report = build_retention_authorization_registry_monitor([record], expected_count=2, observed_at="2026-10-04T11:00:00+00:00")
    assert report["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "REGISTRY_COUNT_MISMATCH" for x in report["findings"])

def test_sequence_gap_requires_control():
    first = dict(_snapshot(), registry_policy_version="phase124-v1")
    second = build_retention_authorization_continuity(
        [_decision()], captured_at="2026-10-04T10:05:00+00:00", sequence=3,
        previous_snapshot_fingerprint=first["snapshot_fingerprint"]
    )
    records = [dict(first, registry_policy_version="phase124-v1"), dict(second, registry_policy_version="phase124-v1")]
    report = build_retention_authorization_registry_monitor(records, expected_count=2, observed_at="2026-10-04T11:00:00+00:00")
    assert report["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "SEQUENCE_GAP" for x in report["findings"])

def test_monitor_registry_reads_phase124_registry():
    with TemporaryDirectory() as directory:
        registry = RetentionAuthorizationHistoryRegistry(Path(directory) / "retention.db")
        snapshot = _snapshot()
        registry.append(snapshot)
        report = monitor_registry(registry, observed_at="2026-10-04T11:00:00+00:00")
        assert report["state"] == "RETENTION_REGISTRY_HEALTHY"
        assert report["snapshot_count"] == 1
        assert report["valid_snapshot_count"] == 1

def test_governance_controls_cannot_be_tampered():
    report = build_retention_authorization_registry_monitor([], expected_count=0, observed_at="2026-10-04T11:00:00+00:00")
    tampered = dict(report, execution_permitted=True)
    with pytest.raises(ValueError, match="MONITOR_FINGERPRINT_MISMATCH"):
        validate_retention_registry_monitor(tampered)
