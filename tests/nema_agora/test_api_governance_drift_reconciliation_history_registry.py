"""Phase 108 tests — persistent reconciliation snapshot history registry."""
from __future__ import annotations

import sqlite3

import pytest

from nema_agora.api_governance_drift_review_reconciliation import reconcile_drift_reviews
from nema_agora.api_governance_drift_reconciliation_history import build_reconciliation_snapshot
from nema_agora.api_governance_drift_reconciliation_history_registry import (
    GovernanceDriftReconciliationHistoryRegistry,
)


def make_snapshot(sequence=1, previous=None, hour=12):
    result = reconcile_drift_reviews([], [], [], [])
    return build_reconciliation_snapshot(
        result,
        captured_at=f"2026-10-04T{hour:02d}:00:00Z",
        sequence=sequence,
        previous_snapshot_fingerprint=previous,
    )


def test_phase108_append_and_read_persisted_history(tmp_path):
    registry = GovernanceDriftReconciliationHistoryRegistry(tmp_path / "history.db")
    first = make_snapshot()
    saved = registry.append(first)
    second = make_snapshot(2, first["snapshot_fingerprint"], 13)
    registry.append(second)
    rows = registry.list()
    assert saved["registry_policy_version"] == "phase108-v1"
    assert [row["sequence"] for row in rows] == [1, 2]
    assert registry.count() == 2
    assert registry.reconcile_history()["state"] == "HISTORY_READY"


def test_phase108_rejects_sequence_gap_and_broken_predecessor(tmp_path):
    registry = GovernanceDriftReconciliationHistoryRegistry(tmp_path / "history.db")
    with pytest.raises(ValueError, match="FIRST_SNAPSHOT_SEQUENCE_REQUIRED"):
        registry.append(make_snapshot(2, "a" * 64))
    first = make_snapshot()
    registry.append(first)
    with pytest.raises(ValueError, match="SNAPSHOT_SEQUENCE_NOT_NEXT"):
        registry.append(make_snapshot(3, "b" * 64, 14))
    with pytest.raises(ValueError, match="SNAPSHOT_PREDECESSOR_MISMATCH"):
        registry.append(make_snapshot(2, "b" * 64, 13))


def test_phase108_rejects_duplicate_and_tampered_snapshots(tmp_path):
    registry = GovernanceDriftReconciliationHistoryRegistry(tmp_path / "history.db")
    first = make_snapshot()
    registry.append(first)
    with pytest.raises(ValueError, match="SNAPSHOT_HISTORY_CONFLICT"):
        registry.append(first)
    tampered = dict(make_snapshot(2, first["snapshot_fingerprint"], 13))
    tampered["state"] = "CONTROL_REQUIRED"
    with pytest.raises(ValueError, match="SNAPSHOT_FINGERPRINT_MISMATCH"):
        registry.append(tampered)


def test_phase108_database_blocks_update_and_delete(tmp_path):
    path = tmp_path / "history.db"
    registry = GovernanceDriftReconciliationHistoryRegistry(path)
    registry.append(make_snapshot())
    with sqlite3.connect(path) as conn:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE governance_drift_reconciliation_snapshots SET state='CONTROL_REQUIRED'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM governance_drift_reconciliation_snapshots")
    assert registry.count() == 1


@pytest.mark.parametrize("limit", [0, -1, 501, True, "10"])
def test_phase108_list_rejects_invalid_limit(tmp_path, limit):
    registry = GovernanceDriftReconciliationHistoryRegistry(tmp_path / "history.db")
    with pytest.raises(ValueError, match="INVALID_LIMIT"):
        registry.list(limit)


def test_phase108_empty_registry_reports_no_history(tmp_path):
    registry = GovernanceDriftReconciliationHistoryRegistry(tmp_path / "history.db")
    assert registry.reconcile_history()["state"] == "NO_HISTORY"
