"""Phase 149 tests — continuity integrity monitor."""

from __future__ import annotations

import sqlite3

import pytest

from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_phase147 import (
    build_authorization_history_registry_decision_history_lifecycle_decision_continuity,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_phase148 import (
    AuthorizationHistoryRegistryDecisionHistoryLifecycleDecisionContinuityRegistry,
)
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_monitor_phase149 import (
    build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor,
    monitor_registry,
    validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor,
)


def test_no_history_requires_review():
    report = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(
        [], observed_at="2026-10-04T10:00:00+00:00"
    )
    assert report["state"] == "NO_HISTORY"
    assert report["recommendation"] == "REVIEW_CONTINUITY"
    assert report["registry_count"] == 0
    assert validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(report) == report


def test_healthy_populated_registry():
    snapshot = build_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        [], captured_at="2026-10-04T09:00:00+00:00", sequence=1
    )
    report = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(
        [snapshot], observed_at="2026-10-04T10:00:00+00:00", expected_count=1
    )
    assert report["state"] == "CONTINUITY_HEALTHY"
    assert report["recommendation"] == "NO_CONTINUITY_ACTION"
    assert report["findings"] == []


def test_sequence_gap_is_control_required():
    first = build_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        [], captured_at="2026-10-04T09:00:00+00:00", sequence=1
    )
    second = build_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        [], captured_at="2026-10-04T09:05:00+00:00", sequence=3,
        previous_snapshot_fingerprint=first["snapshot_fingerprint"]
    )
    report = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(
        [first, second], observed_at="2026-10-04T10:00:00+00:00", expected_count=2
    )
    assert report["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "CONTINUITY_SEQUENCE_GAP" for x in report["findings"])


def test_predecessor_mismatch_is_control_required():
    first = build_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        [], captured_at="2026-10-04T09:00:00+00:00", sequence=1
    )
    second = build_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        [], captured_at="2026-10-04T09:05:00+00:00", sequence=2,
        previous_snapshot_fingerprint="wrong"
    )
    report = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(
        [first, second], observed_at="2026-10-04T10:00:00+00:00"
    )
    assert report["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "CONTINUITY_PREDECESSOR_MISMATCH" for x in report["findings"])


def test_expected_count_mismatch():
    first = build_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        [], captured_at="2026-10-04T09:00:00+00:00", sequence=1
    )
    report = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(
        [first], observed_at="2026-10-04T10:00:00+00:00", expected_count=2
    )
    assert report["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "REGISTRY_COUNT_MISMATCH" for x in report["findings"])


def test_invalid_record_is_detected():
    snapshot = build_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        [], captured_at="2026-10-04T09:00:00+00:00", sequence=1
    )
    tampered = dict(snapshot)
    tampered["snapshot_fingerprint"] = "tampered"
    report = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(
        [tampered], observed_at="2026-10-04T10:00:00+00:00"
    )
    assert report["state"] == "CONTROL_REQUIRED"
    assert any(x["code"] == "INVALID_REGISTRY_RECORD" for x in report["findings"])


def test_execution_tamper_is_detected():
    snapshot = build_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        [], captured_at="2026-10-04T09:00:00+00:00", sequence=1
    )
    tampered = dict(snapshot)
    tampered["execution_gate_closed"] = False
    report = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(
        [tampered], observed_at="2026-10-04T10:00:00+00:00"
    )
    assert report["state"] == "CONTROL_REQUIRED"


def test_monitor_is_deterministic_for_same_inputs():
    snapshot = build_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        [], captured_at="2026-10-04T09:00:00+00:00", sequence=1
    )
    a = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(
        [snapshot], observed_at="2026-10-04T10:00:00+00:00", expected_count=1
    )
    b = build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(
        [snapshot], observed_at="2026-10-04T10:00:00+00:00", expected_count=1
    )
    assert a == b
    assert validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(a) == a


def test_monitor_registry_reads_phase148_registry(tmp_path):
    registry = AuthorizationHistoryRegistryDecisionHistoryLifecycleDecisionContinuityRegistry(
        tmp_path / "continuity.db"
    )
    snapshot = build_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        [], captured_at="2026-10-04T09:00:00+00:00", sequence=1
    )
    registry.append(snapshot)
    report = monitor_registry(registry, observed_at="2026-10-04T10:00:00+00:00")
    assert report["state"] == "CONTINUITY_HEALTHY"
    assert report["registry_count"] == 1


def test_append_only_registry_tamper_remains_blocked(tmp_path):
    registry = AuthorizationHistoryRegistryDecisionHistoryLifecycleDecisionContinuityRegistry(
        tmp_path / "continuity.db"
    )
    snapshot = build_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        [], captured_at="2026-10-04T09:00:00+00:00", sequence=1
    )
    registry.append(snapshot)
    with sqlite3.connect(registry.database_path) as db:
        with pytest.raises(sqlite3.IntegrityError, match="APPEND_ONLY"):
            db.execute(
                "UPDATE authorization_history_registry_decision_history_lifecycle_decision_continuity SET decision_count=1 WHERE sequence=1"
            )
        with pytest.raises(sqlite3.IntegrityError, match="APPEND_ONLY"):
            db.execute(
                "DELETE FROM authorization_history_registry_decision_history_lifecycle_decision_continuity WHERE sequence=1"
            )
