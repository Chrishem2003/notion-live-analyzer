"""End-to-end contract test for governance drift detection through human review."""
from __future__ import annotations

from nema_agora.api_governance_snapshot import build_snapshot
from nema_agora.api_governance_drift import detect_drift
from nema_agora.api_governance_drift_registry import GovernanceDriftRegistry
from nema_agora.api_governance_drift_review_queue import (
    DriftReviewQueue,
    build_drift_review_item,
)
from nema_agora.api_governance_drift_human_review import review_drift
from nema_agora.api_governance_drift_review_registry import GovernanceDriftReviewAuditRegistry
from nema_agora.api_governance_drift_review_reconciliation import reconcile_drift_reviews


def _snapshot(count: int):
    observatory = {
        "state": "READY_FOR_HUMAN_REVIEW",
        "counts": {"audit_events": count},
        "control_required_sources": 0,
    }
    health = {
        "state": "HEALTHY",
        "coverage_state": "COMPLETE",
        "finding_count": 0,
    }
    return build_snapshot(
        observatory=observatory,
        health=health,
        captured_at=f"2026-10-04T12:0{count}:00+00:00",
    )


def test_governance_drift_chain_persists_review_and_reconciles(tmp_path):
    baseline = _snapshot(1)
    current = _snapshot(2)
    drift = detect_drift(baseline=baseline, current=current)
    assert drift["state"] == "REVIEW_TRIGGERED"

    drift_registry = GovernanceDriftRegistry(tmp_path / "drift.db")
    drift_registry.append(drift)

    queue_item = build_drift_review_item(drift)
    queue = DriftReviewQueue(tmp_path / "queue.db")
    queue.enqueue(queue_item)

    audit = review_drift(
        queue_item,
        actor_id="coordinator-1",
        role="coordinator",
        outcome="ACKNOWLEDGED",
        reviewed_at="2026-10-04T12:10:00Z",
    )
    audit_registry = GovernanceDriftReviewAuditRegistry(tmp_path / "review-audit.db")
    audit_registry.append(audit)

    result = reconcile_drift_reviews(
        queue.list(),
        drift_registry.list(),
        [audit],
        audit_registry.list(),
    )

    assert result["state"] == "RECONCILED"
    assert result["findings"] == []
    assert result["read_only"] is True
