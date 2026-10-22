"""Tests for Phase 141 decision-history registry integrity monitoring."""
from __future__ import annotations

from copy import deepcopy

import pytest

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_phase139 import (
    build_authorization_history_registry_decision_continuity,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_monitor_phase141 import (
    build_authorization_history_registry_decision_history_monitor,
    validate_authorization_history_registry_decision_history_monitor,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_phase137 import (
    authorize_authorization_history_registry_decision,
)


def _lifecycle() -> dict:
    payload = {
        "policy_version": "phase136-v1",
        "monitor_fingerprint": "monitor-141",
        "review_fingerprint": "review-141",
        "review_outcome": "ACKNOWLEDGED",
        "lifecycle_state": "ACKNOWLEDGED",
        "evaluated_at": "2026-10-04T12:00:00+00:00",
        "human_governed": True,
        "automatic_repair_performed": False,
        "decision_executed": False,
        "execution_gate_closed": True,
        "execution_permitted": False,
        "execution_performed": False,
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
        "emergency_action": None,
    }
    return dict(payload, lifecycle_fingerprint=fingerprint(payload))


def _decision() -> dict:
    return authorize_authorization_history_registry_decision(
        _lifecycle(),
        actor_id="coordinator-141",
        role="coordinator",
        decision="AUTHORIZE_PRESERVATION",
        decided_at="2026-10-04T12:05:00+00:00",
        rationale="Preserve evidence.",
    )


def _snapshot(sequence: int = 1, previous: str | None = None) -> dict:
    return build_authorization_history_registry_decision_continuity(
        [_decision()],
        captured_at=f"2026-10-04T12:{10 + sequence:02d}:00+00:00",
        sequence=sequence,
        previous_snapshot_fingerprint=previous,
    )


def _record(sequence: int = 1, previous: str | None = None) -> dict:
    return dict(_snapshot(sequence, previous), registry_policy_version="phase140-v1")


def test_empty_registry_is_reviewable() -> None:
    report = build_authorization_history_registry_decision_history_monitor(
        [], expected_count=0, observed_at="2026-10-04T13:00:00+00:00"
    )
    assert report["state"] == "NO_HISTORY"
    assert report["retention_registry_recommendation"] == "REVIEW_RETENTION_REGISTRY"
    validate_authorization_history_registry_decision_history_monitor(report)


def test_healthy_registry_is_deterministic() -> None:
    first = _record()
    second = _record(2, first["snapshot_fingerprint"])
    report = build_authorization_history_registry_decision_history_monitor(
        [first, second], expected_count=2, observed_at="2026-10-04T13:00:00+00:00"
    )
    repeat = build_authorization_history_registry_decision_history_monitor(
        [first, second], expected_count=2, observed_at="2026-10-04T13:00:00+00:00"
    )
    assert report["state"] == "RETENTION_REGISTRY_HEALTHY"
    assert report["valid_snapshot_count"] == 2
    assert report["monitor_fingerprint"] == repeat["monitor_fingerprint"]


def test_policy_and_count_mismatch_require_control() -> None:
    record = _record()
    report = build_authorization_history_registry_decision_history_monitor(
        [dict(record, registry_policy_version="wrong")],
        expected_count=2,
        observed_at="2026-10-04T13:00:00+00:00",
    )
    assert report["state"] == "CONTROL_REQUIRED"
    codes = {item["code"] for item in report["findings"]}
    assert {"REGISTRY_POLICY_MISMATCH", "REGISTRY_COUNT_MISMATCH"} <= codes


def test_sequence_gap_requires_control() -> None:
    first = _record()
    gap = _record(3, first["snapshot_fingerprint"])
    report = build_authorization_history_registry_decision_history_monitor(
        [first, gap], expected_count=2, observed_at="2026-10-04T13:00:00+00:00"
    )
    assert report["state"] == "CONTROL_REQUIRED"
    assert any(item["code"] == "SEQUENCE_GAP" for item in report["findings"])


def test_tampered_execution_boundary_is_rejected() -> None:
    report = build_authorization_history_registry_decision_history_monitor(
        [_record()], expected_count=1, observed_at="2026-10-04T13:00:00+00:00"
    )
    tampered = deepcopy(report)
    tampered["execution_performed"] = True
    with pytest.raises(ValueError, match="EXECUTION_GATE_VIOLATION"):
        validate_authorization_history_registry_decision_history_monitor(tampered)
