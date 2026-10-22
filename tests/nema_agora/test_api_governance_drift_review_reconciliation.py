"""Phase 106 tests — governance drift review audit reconciliation."""
from __future__ import annotations

from nema_agora.api_governance_drift_human_review import review_drift
from nema_agora.api_governance_drift_review_queue import build_drift_review_item
from nema_agora.api_governance_drift_review_reconciliation import reconcile_drift_reviews
from nema_agora.api_governance_drift_review_registry import GovernanceDriftReviewAuditRegistry


def fixtures():
    drift = {
        "drift_id": "API-DRIFT-001",
        "drift_fingerprint": "a" * 64,
        "baseline_snapshot_id": "API-SNAPSHOT-BASE",
        "current_snapshot_id": "API-SNAPSHOT-CURRENT",
        "severity": "MEDIUM",
        "state": "REVIEW_TRIGGERED",
    }
    queue = build_drift_review_item(drift)
    audit = review_drift(
        queue, actor_id="coordinator-1", role="coordinator",
        outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:00:00Z",
    )
    return drift, queue, audit


def test_phase106_valid_chain_reconciles(tmp_path):
    drift, queue, audit = fixtures()
    registry = GovernanceDriftReviewAuditRegistry(tmp_path / "audit.db")
    registry.append(audit)
    result = reconcile_drift_reviews([queue], [drift], [audit], registry.list())
    assert result["state"] == "RECONCILED"
    assert result["findings"] == []
    assert result["read_only"] is True


def test_phase106_missing_persisted_audit_requires_control(tmp_path):
    drift, queue, audit = fixtures()
    result = reconcile_drift_reviews([queue], [drift], [audit], [])
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(f["code"] == "MISSING_PERSISTED_AUDIT" for f in result["findings"])


def test_phase106_tampered_persisted_record_is_detected(tmp_path):
    drift, queue, audit = fixtures()
    persisted = dict(audit, policy_version="phase105-v1")
    persisted["outcome"] = "ESCALATED"
    result = reconcile_drift_reviews([queue], [drift], [audit], [persisted])
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(f["code"] == "PERSISTED_AUDIT_MISMATCH" for f in result["findings"])


def test_phase106_orphan_audit_and_missing_drift_are_detected():
    drift, queue, audit = fixtures()
    queue["drift_id"] = "API-DRIFT-MISSING"
    result = reconcile_drift_reviews([queue], [drift], [audit], [])
    codes = {f["code"] for f in result["findings"]}
    assert "MISSING_DRIFT_EVENT" in codes
    assert "QUEUE_AUDIT_BINDING_MISMATCH" in codes
    assert "MISSING_PERSISTED_AUDIT" in codes


def test_phase106_duplicate_records_fail_closed():
    drift, queue, audit = fixtures()
    result = reconcile_drift_reviews([queue, dict(queue)], [drift], [audit], [])
    assert result["state"] == "CONTROL_REQUIRED"
    assert any(f["code"] == "DUPLICATE_RECORD" for f in result["findings"])
