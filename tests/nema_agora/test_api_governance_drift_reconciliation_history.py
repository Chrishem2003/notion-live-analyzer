"""Phase 107 tests — reconciliation snapshot integrity and history."""
from __future__ import annotations

import pytest

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_review_reconciliation import reconcile_drift_reviews
from nema_agora.api_governance_drift_reconciliation_history import (
    build_reconciliation_snapshot,
    build_snapshot_history,
    validate_reconciliation_snapshot,
)


def reconciliation():
    return reconcile_drift_reviews([], [], [], [])


def snapshot(sequence=1, previous=None, captured_at="2026-10-04T12:00:00Z", source=None):
    return build_reconciliation_snapshot(
        source if source is not None else reconciliation(),
        captured_at=captured_at,
        sequence=sequence,
        previous_snapshot_fingerprint=previous,
    )


def test_phase107_builds_valid_read_only_snapshot():
    source = reconciliation()
    before = dict(source)
    result = snapshot(source=source)
    assert result["state"] == "RECONCILED"
    assert result["finding_count"] == 0
    assert result["read_only"] is True
    assert validate_reconciliation_snapshot(result) == result
    assert source == before
    assert result["environmental_conclusion"] is None
    assert result["regulatory_conclusion"] is None


def test_phase107_rejects_tampered_reconciliation():
    source = reconciliation()
    source["state"] = "CONTROL_REQUIRED"
    with pytest.raises(ValueError, match="INVALID_PHASE106_RECONCILIATION"):
        snapshot(source=source)


@pytest.mark.parametrize("kwargs", [
    {"sequence": 0},
    {"sequence": True},
    {"sequence": 1, "previous": "a" * 64},
    {"sequence": 2},
    {"sequence": 2, "previous": "bad"},
    {"sequence": 1, "captured_at": ""},
])
def test_phase107_rejects_invalid_snapshot_inputs(kwargs):
    with pytest.raises(ValueError):
        snapshot(**kwargs)


def test_phase107_history_accepts_contiguous_linked_snapshots():
    first = snapshot()
    second = snapshot(
        sequence=2,
        previous=first["snapshot_fingerprint"],
        captured_at="2026-10-04T13:00:00Z",
    )
    result = build_snapshot_history([first, second])
    assert result["state"] == "HISTORY_READY"
    assert result["snapshot_count"] == 2
    assert result["findings"] == []
    assert len(result["history_fingerprint"]) == 64


def test_phase107_history_detects_broken_predecessor_and_gap():
    first = snapshot()
    third = snapshot(sequence=3, previous="b" * 64)
    result = build_snapshot_history([first, third])
    codes = {item["code"] for item in result["findings"]}
    assert result["state"] == "CONTROL_REQUIRED"
    assert "SEQUENCE_GAP" in codes
    assert "PREDECESSOR_MISMATCH" in codes


def test_phase107_history_detects_tampering_and_duplicate_identity():
    first = snapshot()
    tampered = dict(first, state="CONTROL_REQUIRED")
    result = build_snapshot_history([first, tampered])
    codes = {item["code"] for item in result["findings"]}
    assert result["state"] == "CONTROL_REQUIRED"
    assert "INVALID_SNAPSHOT" in codes
    assert "DUPLICATE_SNAPSHOT_ID" in codes
    assert "DUPLICATE_SEQUENCE" in codes


def test_phase107_empty_history_is_explicit():
    result = build_snapshot_history([])
    assert result["state"] == "NO_HISTORY"
    assert result["snapshot_count"] == 0
