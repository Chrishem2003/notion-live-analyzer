"""Phase 109 tests — reconciliation history integrity monitoring."""
from __future__ import annotations

import sqlite3

import pytest

from nema_agora.api_governance_drift_review_reconciliation import reconcile_drift_reviews
from nema_agora.api_governance_drift_reconciliation_history import build_reconciliation_snapshot
from nema_agora.api_governance_drift_reconciliation_history_registry import (
    GovernanceDriftReconciliationHistoryRegistry,
)
from nema_agora.api_governance_drift_reconciliation_monitor import (
    build_history_integrity_monitor,
    monitor_registry,
)


def make_snapshot(sequence=1, previous=None, hour=12):
    reconciliation = reconcile_drift_reviews([], [], [], [])
    return build_reconciliation_snapshot(
        reconciliation,
        captured_at=f"2026-10-04T{hour:02d}:00:00Z",
        sequence=sequence,
        previous_snapshot_fingerprint=previous,
    )


def stored(*snapshots):
    return [dict(item, registry_policy_version="phase108-v1") for item in snapshots]


def test_phase109_clean_registry_history_is_monitoring_clear(tmp_path):
    registry = GovernanceDriftReconciliationHistoryRegistry(tmp_path / "history.db")
    first = make_snapshot()
    registry.append(first)
    second = make_snapshot(2, first["snapshot_fingerprint"], 13)
    registry.append(second)
    report = monitor_registry(registry, observed_at="2026-10-04T14:00:00Z")
    assert report["state"] == "MONITORING_CLEAR"
    assert report["recovery_recommendation"] == "NO_RECOVERY_ACTION"
    assert report["automatic_repair_performed"] is False
    assert report["read_only"] is True


def test_phase109_empty_history_is_explicit(tmp_path):
    registry = GovernanceDriftReconciliationHistoryRegistry(tmp_path / "history.db")
    report = monitor_registry(registry, observed_at="2026-10-04T14:00:00Z")
    assert report["state"] == "NO_HISTORY"
    assert report["recovery_recommendation"] == "REVIEW_BACKUP"
    assert report["recovery_required"] is False


def test_phase109_detects_tampering_without_repairing():
    first = make_snapshot()
    tampered = dict(stored(first)[0])
    tampered["state"] = "CONTROL_REQUIRED"
    report = build_history_integrity_monitor(
        [tampered], expected_count=1, observed_at="2026-10-04T14:00:00Z"
    )
    assert report["state"] == "CONTROL_REQUIRED"
    assert "INVALID_SNAPSHOT" in {item["code"] for item in report["findings"]}
    assert report["automatic_repair_performed"] is False


def test_phase109_detects_registry_policy_mismatch():
    report = build_history_integrity_monitor(
        [dict(stored(make_snapshot())[0], registry_policy_version="unknown-v9")],
        expected_count=1, observed_at="2026-10-04T14:00:00Z",
    )
    assert report["state"] == "CONTROL_REQUIRED"
    assert "REGISTRY_POLICY_MISMATCH" in {item["code"] for item in report["findings"]}


def test_phase109_detects_count_mismatch_and_sequence_gap():
    first = make_snapshot()
    third = make_snapshot(3, "a" * 64, 14)
    report = build_history_integrity_monitor(
        stored(first, third), expected_count=3, observed_at="2026-10-04T14:00:00Z"
    )
    codes = {item["code"] for item in report["findings"]}
    assert report["state"] == "CONTROL_REQUIRED"
    assert "REGISTRY_COUNT_MISMATCH" in codes
    assert "SEQUENCE_GAP" in codes


def test_phase109_detects_duplicate_fingerprints():
    first = make_snapshot()
    duplicate = dict(first, sequence=2, previous_snapshot_fingerprint=first["snapshot_fingerprint"])
    report = build_history_integrity_monitor(
        stored(first, duplicate), expected_count=2, observed_at="2026-10-04T14:00:00Z"
    )
    codes = {item["code"] for item in report["findings"]}
    assert "DUPLICATE_SNAPSHOT_FINGERPRINT" in codes
    assert report["state"] == "CONTROL_REQUIRED"


@pytest.mark.parametrize("count", [-1, True, "2"])
def test_phase109_rejects_invalid_expected_count(count):
    with pytest.raises(ValueError, match="INVALID_EXPECTED_COUNT"):
        build_history_integrity_monitor([], expected_count=count, observed_at="2026-10-04T14:00:00Z")


@pytest.mark.parametrize("records", ["not-records", b"no", None])
def test_phase109_rejects_invalid_record_collection(records):
    with pytest.raises(ValueError, match="INVALID_REGISTRY_RECORDS"):
        build_history_integrity_monitor(records, observed_at="2026-10-04T14:00:00Z")


def test_phase109_report_is_deterministic_for_same_observation():
    records = stored(make_snapshot())
    left = build_history_integrity_monitor(records, expected_count=1, observed_at="2026-10-04T14:00:00Z")
    right = build_history_integrity_monitor(records, expected_count=1, observed_at="2026-10-04T14:00:00Z")
    assert left["monitor_fingerprint"] == right["monitor_fingerprint"]


def test_phase109_database_remains_unchanged_after_monitoring(tmp_path):
    path = tmp_path / "history.db"
    registry = GovernanceDriftReconciliationHistoryRegistry(path)
    registry.append(make_snapshot())
    before = registry.count()
    monitor_registry(registry, observed_at="2026-10-04T14:00:00Z")
    assert registry.count() == before
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM governance_drift_reconciliation_snapshots").fetchone()[0] == 1
