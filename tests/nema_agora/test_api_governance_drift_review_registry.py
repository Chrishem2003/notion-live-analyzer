"""Phase 105 tests — persistent governance drift review audit registry."""
from __future__ import annotations

import sqlite3

import pytest

from nema_agora.api_governance_drift_human_review import review_drift
from nema_agora.api_governance_drift_review_registry import (
    GovernanceDriftReviewAuditRegistry,
    POLICY_VERSION,
    validate_review_audit,
)
from nema_agora.api_audit_binding import fingerprint


def _item():
    return {
        "review_id": "API-DRIFT-REVIEW-001",
        "drift_id": "API-DRIFT-001",
        "drift_fingerprint": "a" * 64,
        "baseline_snapshot_id": "API-SNAPSHOT-BASE",
        "current_snapshot_id": "API-SNAPSHOT-CURRENT",
        "state": "QUEUED",
    }


def _audit():
    return review_drift(
        _item(),
        actor_id="reviewer-1",
        role="coordinator",
        outcome="ACKNOWLEDGED",
        reviewed_at="2026-10-04T12:00:00Z",
    )


def test_phase105_review_audit_is_validated_and_deterministic():
    audit = _audit()
    assert validate_review_audit(audit)["audit_id"] == audit["audit_id"]
    assert audit["audit_fingerprint"] == fingerprint({
        "review_id": audit["review_id"],
        "drift_id": audit["drift_id"],
        "drift_fingerprint": audit["drift_fingerprint"],
        "baseline_snapshot_id": audit["baseline_snapshot_id"],
        "current_snapshot_id": audit["current_snapshot_id"],
        "reviewer_actor_id": audit["reviewer_actor_id"],
        "reviewer_role": audit["reviewer_role"],
        "outcome": audit["outcome"],
        "reviewed_at": audit["reviewed_at"],
    })


def test_phase105_append_and_list_are_persistent(tmp_path):
    registry = GovernanceDriftReviewAuditRegistry(tmp_path / "audit.db")
    audit = _audit()
    stored = registry.append(audit)
    assert stored["policy_version"] == POLICY_VERSION
    assert registry.list() == [stored]


def test_phase105_duplicate_review_is_rejected(tmp_path):
    registry = GovernanceDriftReviewAuditRegistry(tmp_path / "audit.db")
    audit = _audit()
    registry.append(audit)
    with pytest.raises(ValueError, match="DRIFT_REVIEW_AUDIT_CONFLICT"):
        registry.append(audit)


def test_phase105_tampered_fingerprint_fails_closed(tmp_path):
    audit = _audit()
    audit["audit_fingerprint"] = "b" * 64
    with pytest.raises(ValueError, match="REVIEW_AUDIT_FINGERPRINT_MISMATCH"):
        validate_review_audit(audit)


def test_phase105_invalid_limit_fails_closed(tmp_path):
    registry = GovernanceDriftReviewAuditRegistry(tmp_path / "audit.db")
    with pytest.raises(ValueError, match="INVALID_LIMIT"):
        registry.list(0)


def test_phase105_database_is_append_only(tmp_path):
    registry = GovernanceDriftReviewAuditRegistry(tmp_path / "audit.db")
    audit = _audit()
    registry.append(audit)
    with sqlite3.connect(tmp_path / "audit.db") as conn:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute(
                "UPDATE governance_drift_review_audits SET outcome='ESCALATED' WHERE audit_id=?",
                (audit["audit_id"],),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute(
                "DELETE FROM governance_drift_review_audits WHERE audit_id=?",
                (audit["audit_id"],),
            )
