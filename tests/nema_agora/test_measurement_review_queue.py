from __future__ import annotations

import pytest

from nema_agora.measurement_review_queue import (
    MeasurementReviewQueueError,
    load_measurement_review_queue,
)


class FakeRepository:
    def __init__(self):
        self.measurements = [{
            "measurement_id": "m-001",
            "indicator_id": "ENV-ALERT-001",
            "status": "measured",
            "value": 4,
            "created_at": "2026-10-27T10:00:00+03:00",
        }]
        self.events = [{
            "audit_id": "m-001:submitted",
            "measurement_id": "m-001",
            "actor_id": "submitter-2",
            "actor_role": "submitter",
            "action": "measurement_submitted",
            "created_at": "2026-10-27T10:00:00+03:00",
        }]
        self.calls = []

    def list_indicator_measurements(self, **kwargs):
        self.calls.append(("measurements", kwargs))
        return self.measurements

    def list_measurement_audit_events(self, measurement_id, **kwargs):
        self.calls.append(("audit", measurement_id, kwargs))
        return self.events


def test_queue_loads_canonical_measured_records_and_audit_without_writes():
    repo = FakeRepository()
    queue = load_measurement_review_queue(
        principal={"authenticated": True, "subject": "reviewer-9", "role": "reviewer"},
        repository=repo,
    )
    assert queue[0]["measurement"]["measurement_id"] == "m-001"
    assert queue[0]["submission_audit_present"] is True
    assert queue[0]["submission_actor_ids"] == ["submitter-2"]
    assert queue[0]["reviewer_can_self_review"] is True
    assert [call[0] for call in repo.calls] == ["measurements", "audit"]


def test_submitter_cannot_enter_officer_review_queue():
    repo = FakeRepository()
    with pytest.raises(MeasurementReviewQueueError, match="cannot view"):
        load_measurement_review_queue(
            principal={"authenticated": True, "subject": "submitter-2", "role": "submitter"},
            repository=repo,
        )
    assert repo.calls == []


def test_unauthenticated_user_cannot_enter_queue():
    repo = FakeRepository()
    with pytest.raises(MeasurementReviewQueueError, match="verified authenticated"):
        load_measurement_review_queue(
            principal={"authenticated": False, "subject": "x", "role": "admin"},
            repository=repo,
        )


def test_missing_submission_audit_is_flagged_not_silently_accepted():
    repo = FakeRepository()
    repo.events = []
    queue = load_measurement_review_queue(
        principal={"authenticated": True, "subject": "reviewer-9", "role": "reviewer"},
        repository=repo,
    )
    assert queue[0]["submission_audit_present"] is False
    assert "No submission audit" in queue[0]["audit_warning"]


def test_submitter_is_detected_from_audit_and_cannot_self_review():
    repo = FakeRepository()
    queue = load_measurement_review_queue(
        principal={"authenticated": True, "subject": "submitter-2", "role": "coordinator"},
        repository=repo,
    )
    assert queue[0]["reviewer_can_self_review"] is False
