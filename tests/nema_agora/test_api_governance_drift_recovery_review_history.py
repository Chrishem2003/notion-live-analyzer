"""Phase 112 — recovery-review snapshot and history tests."""
import sqlite3
import pytest

from nema_agora.api_governance_drift_recovery_review_ledger import review_recovery_recommendation
from nema_agora.api_governance_drift_reconciliation_monitor import build_history_integrity_monitor
from nema_agora.api_governance_drift_recovery_review_reconciliation import reconcile_recovery_reviews
from nema_agora.api_governance_drift_recovery_review_history import (
    build_recovery_review_snapshot, reconcile_recovery_review_snapshot_history,
)
from nema_agora.api_governance_drift_recovery_review_history_registry import RecoveryReviewSnapshotHistoryRegistry


def source():
    report = build_history_integrity_monitor([], expected_count=0, observed_at="2026-10-10T09:00:00Z")
    review = review_recovery_recommendation(report, actor_id="demo-reviewer", role="coordinator",
        outcome="BACKUP_REVIEWED", reviewed_at="2026-10-10T09:10:00Z", notes="synthetic")
    review["ledger_policy_version"] = "phase110-v1"
    return reconcile_recovery_reviews([report], [review], expected_ledger_count=1)


def snap(sequence=1, predecessor=None, result=None):
    return build_recovery_review_snapshot(result or source(), captured_at=f"2026-10-10T09:{sequence:02d}:00Z",
        sequence=sequence, predecessor_fingerprint=predecessor)


def test_snapshot_is_fingerprinted_and_bound_to_phase111():
    item = snap()
    assert item["policy_version"] == "phase112-v1"
    assert item["snapshot_id"].endswith(item["snapshot_fingerprint"][:24])
    assert item["read_only"] is True and item["automatic_recovery_performed"] is False


def test_tampered_reconciliation_is_rejected():
    result = source()
    result["state"] = "RECONCILED"
    with pytest.raises(ValueError, match="RECONCILIATION_FINGERPRINT_MISMATCH"):
        snap(result=result)


def test_history_clean_and_empty_states():
    assert reconcile_recovery_review_snapshot_history([])["state"] == "NO_HISTORY"
    first = snap()
    second = snap(2, first["snapshot_fingerprint"])
    result = reconcile_recovery_review_snapshot_history([first, second])
    assert result["state"] == "HISTORY_RECONCILED"
    assert result["findings"] == []


def test_history_detects_sequence_gap_and_broken_predecessor():
    first = snap()
    third = snap(3, "a" * 64)
    result = reconcile_recovery_review_snapshot_history([first, third])
    codes = {item["code"] for item in result["findings"]}
    assert "SEQUENCE_GAP" in codes and "PREDECESSOR_MISMATCH" in codes
    assert result["state"] == "CONTROL_REQUIRED"


def test_history_detects_snapshot_tampering():
    item = snap()
    item["finding_count"] = 99
    result = reconcile_recovery_review_snapshot_history([item])
    assert result["state"] == "CONTROL_REQUIRED"
    assert result["findings"][0]["code"] == "INVALID_SNAPSHOT"


def test_registry_enforces_sequence_and_chain(tmp_path):
    registry = RecoveryReviewSnapshotHistoryRegistry(tmp_path / "snapshots.db")
    first = snap()
    registry.append(first)
    second = snap(2, first["snapshot_fingerprint"])
    registry.append(second)
    assert registry.count() == 2
    assert registry.integrity_report()["state"] == "HISTORY_RECONCILED"
    with pytest.raises(ValueError, match="INVALID_NEXT_SEQUENCE"):
        registry.append(snap(4, second["snapshot_fingerprint"]))


def test_registry_blocks_update_and_delete(tmp_path):
    path = tmp_path / "snapshots.db"
    registry = RecoveryReviewSnapshotHistoryRegistry(path)
    registry.append(snap())
    with sqlite3.connect(path) as conn:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE recovery_review_snapshot_history SET sequence=2")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM recovery_review_snapshot_history")
    assert registry.count() == 1


@pytest.mark.parametrize("limit", [0, -1, 501, True, "20"])
def test_registry_rejects_invalid_limits(tmp_path, limit):
    registry = RecoveryReviewSnapshotHistoryRegistry(tmp_path / "snapshots.db")
    with pytest.raises(ValueError, match="INVALID_LIMIT"):
        registry.list(limit)
