from datetime import date

import pytest

from nema_agora.core import CATEGORIES, make_observation
from nema_agora.storage import NemaAgoraRepository


def sample_record():
    return make_observation(
        observation_date=date(2026, 10, 4),
        category=CATEGORIES[0],
        severity="Moderate",
        site="Pilot A",
        description="Synthetic test observation",
        latitude=2.5,
        longitude=32.1,
        consent_confirmed=True,
        created_at="2026-10-04T12:00:00+03:00",
    )


def test_create_and_read_observation_persists_between_repository_instances(tmp_path):
    path = tmp_path / "pilot.sqlite3"
    first = NemaAgoraRepository(path)
    created = first.create_observation(sample_record(), actor_id="submitter-1", role="submitter")

    second = NemaAgoraRepository(path)
    assert second.get_observation(created["case_id"], actor_id="submitter-1", role="submitter") == created
    assert second.list_observations(actor_id="submitter-1", role="submitter", status="Received") == [created]


def test_creation_writes_audit_event_with_actor(tmp_path):
    repository = NemaAgoraRepository(tmp_path / "pilot.sqlite3")
    record = repository.create_observation(sample_record(), actor_id="submitter-1", role="submitter")

    events = repository.list_audit_events(record["case_id"], actor_id="admin-1", role="admin")
    assert len(events) == 1
    assert events[0]["event_type"] == "record_created"
    assert events[0]["actor_id"] == "reviewer-1"
    assert events[0]["from_status"] is None
    assert events[0]["to_status"] == "Received"


def test_status_update_and_audit_event_are_saved(tmp_path):
    repository = NemaAgoraRepository(tmp_path / "pilot.sqlite3")
    record = repository.create_observation(sample_record(), actor_id="submitter-1", role="submitter")

    updated = repository.update_review(
        record["case_id"],
        actor_id="reviewer-2", role="reviewer",
        new_status="Under review",
        review_notes="Initial triage",
        changed_at="2026-10-04T12:10:00+03:00",
    )
    events = repository.list_audit_events(record["case_id"], actor_id="admin-1", role="admin")

    assert updated["status"] == "Under review"
    assert updated["review_notes"] == "Initial triage"
    assert events[-1]["event_type"] == "status_changed"
    assert events[-1]["actor_id"] == "reviewer-2"
    assert events[-1]["from_status"] == "Received"
    assert events[-1]["to_status"] == "Under review"


def test_invalid_transition_does_not_change_record_or_add_event(tmp_path):
    repository = NemaAgoraRepository(tmp_path / "pilot.sqlite3")
    record = repository.create_observation(sample_record(), actor_id="submitter-1", role="submitter")

    with pytest.raises(ValueError, match="cannot move directly"):
        repository.update_review(
            record["case_id"],
            actor_id="reviewer-2", role="reviewer",
            new_status="Closed",
            review_notes="",
            changed_at="now",
        )

    assert repository.get_observation(record["case_id"], actor_id="submitter-1", role="submitter")["status"] == "Received"
    assert len(repository.list_audit_events(record["case_id"], actor_id="reviewer-2", role="reviewer")) == 1


def test_unknown_case_and_missing_actor_are_rejected(tmp_path):
    repository = NemaAgoraRepository(tmp_path / "pilot.sqlite3")
    with pytest.raises(ValueError, match="authenticated actor"):
        repository.create_observation(sample_record(), actor_id=" ", role="submitter")
    with pytest.raises(KeyError, match="Case not found"):
        repository.update_review(
            "NA-NOTFOUND",
            actor_id="reviewer-1", role="reviewer",
            new_status="Under review",
            review_notes="",
            changed_at="now",
        )


def test_duplicate_case_id_is_not_silently_overwritten(tmp_path):
    repository = NemaAgoraRepository(tmp_path / "pilot.sqlite3")
    record = sample_record()
    repository.create_observation(record, actor_id="submitter-1", role="submitter")
    with pytest.raises(Exception):
        repository.create_observation(record, actor_id="submitter-1", role="submitter")
    assert len(repository.list_observations(actor_id="submitter-1", role="submitter")) == 1


def test_submitter_cannot_read_other_users_record(tmp_path):
    repo = NemaAgoraRepository(tmp_path / "pilot.sqlite3")
    record = repo.create_observation(sample_record(), actor_id="submitter-1", role="submitter")
    with pytest.raises(PermissionError):
        repo.get_observation(record["case_id"], actor_id="submitter-2", role="submitter")


def test_submitter_cannot_review_or_read_audit(tmp_path):
    repo = NemaAgoraRepository(tmp_path / "pilot.sqlite3")
    record = repo.create_observation(sample_record(), actor_id="submitter-1", role="submitter")
    with pytest.raises(PermissionError):
        repo.update_review(record["case_id"], actor_id="submitter-1", role="submitter",
                           new_status="Under review", review_notes="", changed_at="now")
    with pytest.raises(PermissionError):
        repo.list_audit_events(record["case_id"], actor_id="submitter-1", role="submitter")


def test_intelligence_feedback_is_audited_and_bounded(tmp_path):
    repo = NemaAgoraRepository(tmp_path / "pilot.sqlite3")
    record = repo.create_observation(sample_record(), actor_id="submitter-1", role="submitter")
    repo.record_intelligence_event(
        record["case_id"], actor_id="reviewer-1", role="reviewer",
        event_type="analysis_run", occurred_at="2026-10-04T12:01:00+03:00",
        details={"copilot_version": "phase10-v1"},
    )
    repo.record_intelligence_feedback(
        record["case_id"], actor_id="reviewer-1", role="reviewer",
        feedback={"feedback_type": "corrected", "corrected_category": CATEGORIES[1],
                  "notes": "Synthetic evaluation note", "copilot_version": "phase10-v1"},
        occurred_at="2026-10-04T12:02:00+03:00",
    )
    events = repo.list_intelligence_events(record["case_id"], actor_id="admin-1", role="admin")
    assert [e["event_type"] for e in events] == ["analysis_run", "feedback_recorded"]
    assert events[-1]["details"]["feedback_type"] == "corrected"


def test_submitter_cannot_write_intelligence_feedback(tmp_path):
    repo = NemaAgoraRepository(tmp_path / "pilot.sqlite3")
    record = repo.create_observation(sample_record(), actor_id="submitter-1", role="submitter")
    with pytest.raises(PermissionError):
        repo.record_intelligence_feedback(
            record["case_id"], actor_id="submitter-1", role="submitter",
            feedback={"feedback_type": "accepted"},
            occurred_at="2026-10-04T12:02:00+03:00",
        )
