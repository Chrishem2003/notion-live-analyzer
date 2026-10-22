import pytest
from nema_agora.api_governance_drift_human_review import review_drift
from nema_agora.api_governance_drift_review_queue import build_drift_review_item


def item():
    drift = {
        "drift_id": "API-DRIFT-1",
        "drift_fingerprint": "a" * 64,
        "baseline_snapshot_id": "API-SNAPSHOT-A",
        "current_snapshot_id": "API-SNAPSHOT-B",
        "severity": "MEDIUM",
        "state": "REVIEW_TRIGGERED",
    }
    return build_drift_review_item(drift)


def test_review():
    assert review_drift(
        item(), actor_id="reviewer-1", role="coordinator",
        outcome="INVESTIGATE", reviewed_at="2026-10-04T12:00:00+00:00"
    )["state"] == "REVIEW_RECORDED"


def test_unauthorized():
    with pytest.raises(ValueError, match="REVIEWER_NOT_AUTHORIZED"):
        review_drift(
            item(), actor_id="reviewer-1", role="reviewer",
            outcome="INVESTIGATE", reviewed_at="2026-10-04T12:00:00Z"
        )


def test_not_queued():
    queued = item()
    queued["state"] = "CLOSED"
    with pytest.raises(ValueError, match="REVIEW_ITEM_NOT_QUEUED"):
        review_drift(
            queued, actor_id="admin-1", role="admin",
            outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:00:00Z"
        )


def test_rejects_invalid_actor_id_and_timezone_missing():
    with pytest.raises(ValueError, match="INVALID_REVIEWER_ID"):
        review_drift(
            item(), actor_id="bad actor", role="admin",
            outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:00:00Z"
        )
    with pytest.raises(ValueError, match="INVALID_REVIEW_TIME"):
        review_drift(
            item(), actor_id="admin-1", role="admin",
            outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:00:00"
        )


def test_rejects_tampered_queue_item_before_recording_review():
    queued = item()
    queued["priority"] = 100
    with pytest.raises(ValueError, match="REVIEW_ITEM_ID_MISMATCH"):
        review_drift(
            queued, actor_id="admin-1", role="admin",
            outcome="ACKNOWLEDGED", reviewed_at="2026-10-04T12:00:00Z"
        )
