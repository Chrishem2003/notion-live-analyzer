"""Phase 110 tests — human-acknowledged recovery review ledger."""
from __future__ import annotations

import sqlite3

import pytest

from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_reconciliation_monitor import build_history_integrity_monitor
from nema_agora.api_governance_drift_reconciliation_history import build_reconciliation_snapshot
from nema_agora.api_governance_drift_review_reconciliation import reconcile_drift_reviews
from nema_agora.api_governance_drift_reconciliation_history_registry import GovernanceDriftReconciliationHistoryRegistry
from nema_agora.api_governance_drift_reconciliation_monitor import monitor_registry
from nema_agora.api_governance_drift_recovery_review_ledger import (
    RecoveryReviewLedger,
    review_recovery_recommendation,
    validate_monitor_report,
)


def monitor_report():
    return build_history_integrity_monitor([], expected_count=0, observed_at="2026-10-04T14:00:00Z")


def control_required_report():
    base = monitor_report()
    payload = dict(base)
    payload.pop("monitor_fingerprint")
    payload["state"] = "CONTROL_REQUIRED"
    payload["findings"] = [{"code": "SYNTHETIC_INTEGRITY_FINDING"}]
    payload["recovery_recommendation"] = "PRESERVE_AND_ESCALATE"
    payload["recovery_required"] = True
    return dict(payload, monitor_fingerprint=fingerprint(payload))


def make_review(report=None, **kwargs):
    return review_recovery_recommendation(
        report or monitor_report(),
        actor_id=kwargs.get("actor_id", "reviewer-1"),
        role=kwargs.get("role", "coordinator"),
        outcome=kwargs.get("outcome", "BACKUP_REVIEWED"),
        reviewed_at=kwargs.get("reviewed_at", "2026-10-04T15:00:00Z"),
        notes=kwargs.get("notes", "Synthetic review note"),
    )


def test_phase110_records_authorized_human_review(tmp_path):
    ledger = RecoveryReviewLedger(tmp_path / "reviews.db")
    saved = ledger.append(make_review())
    assert saved["state"] == "REVIEW_RECORDED"
    assert saved["ledger_policy_version"] == "phase110-v1"
    assert saved["automatic_recovery_performed"] is False
    assert ledger.count() == 1
    assert ledger.list()[0]["monitor_fingerprint"] == monitor_report()["monitor_fingerprint"]


def test_phase110_rejects_unauthorized_role():
    with pytest.raises(ValueError, match="REVIEWER_NOT_AUTHORIZED"):
        make_review(role="observer")


def test_phase110_rejects_tampered_monitor_report():
    report = monitor_report()
    report["recovery_recommendation"] = "NO_ACTION_APPROVED"
    with pytest.raises(ValueError, match="MONITOR_REPORT_FINGERPRINT_MISMATCH"):
        validate_monitor_report(report)


def test_phase110_blocks_no_action_for_control_required_report():
    with pytest.raises(ValueError, match="NO_ACTION_NOT_ALLOWED_WHILE_CONTROL_REQUIRED"):
        make_review(control_required_report(), outcome="NO_ACTION_APPROVED")


def test_phase110_rejects_duplicate_monitor_review(tmp_path):
    ledger = RecoveryReviewLedger(tmp_path / "reviews.db")
    review = make_review()
    ledger.append(review)
    with pytest.raises(ValueError, match="RECOVERY_REVIEW_CONFLICT"):
        ledger.append(review)


def test_phase110_review_tampering_fails_validation(tmp_path):
    ledger = RecoveryReviewLedger(tmp_path / "reviews.db")
    review = make_review()
    tampered = dict(review, outcome="ESCALATED")
    with pytest.raises(ValueError, match="RECOVERY_REVIEW_FINGERPRINT_MISMATCH"):
        ledger.append(tampered)


def test_phase110_sqlite_blocks_update_delete(tmp_path):
    path = tmp_path / "reviews.db"
    ledger = RecoveryReviewLedger(path)
    ledger.append(make_review())
    with sqlite3.connect(path) as conn:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE recovery_review_ledger SET outcome='ESCALATED'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM recovery_review_ledger")
    assert ledger.count() == 1


@pytest.mark.parametrize("limit", [0, -1, 501, True, "10"])
def test_phase110_rejects_invalid_list_limits(tmp_path, limit):
    ledger = RecoveryReviewLedger(tmp_path / "reviews.db")
    with pytest.raises(ValueError, match="INVALID_LIMIT"):
        ledger.list(limit)


def test_phase110_review_report_binds_exact_monitor_fingerprint():
    report = monitor_report()
    review = make_review(report)
    assert review["monitor_fingerprint"] == report["monitor_fingerprint"]
    assert review["monitor_state"] == report["state"]
    assert review["recovery_recommendation"] == report["recovery_recommendation"]


def test_phase110_registry_monitoring_is_read_only(tmp_path):
    history = GovernanceDriftReconciliationHistoryRegistry(tmp_path / "history.db")
    reconciliation = reconcile_drift_reviews([], [], [], [])
    snapshot = build_reconciliation_snapshot(reconciliation, captured_at="2026-10-04T12:00:00Z", sequence=1)
    history.append(snapshot)
    before = history.count()
    report = monitor_registry(history, observed_at="2026-10-04T14:00:00Z")
    ledger = RecoveryReviewLedger(tmp_path / "reviews.db")
    ledger.append(make_review(report, outcome="ACKNOWLEDGED"))
    assert history.count() == before
    assert ledger.count() == 1
