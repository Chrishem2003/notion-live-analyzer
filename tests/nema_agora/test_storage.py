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
    assert events[0]["actor_id"] == "submitter-1"
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
            changed_at="2026-10-04T12:10:00+03:00",
        )

    assert repository.get_observation(record["case_id"], actor_id="submitter-1", role="submitter")["status"] == "Received"
    assert len(repository.list_audit_events(record["case_id"], actor_id="admin-1", role="admin")) == 1


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
            changed_at="2026-10-04T12:10:00+03:00",
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

def test_review_rejects_timezone_naive_or_malformed_audit_timestamp(tmp_path):
    repo = NemaAgoraRepository(tmp_path / "pilot.sqlite3")
    record = repo.create_observation(sample_record(), actor_id="submitter-1", role="submitter")

    for invalid_timestamp in ("now", "2026-10-04T12:10:00", ""):
        with pytest.raises(ValueError, match="ISO 8601 timestamp with timezone"):
            repo.update_review(
                record["case_id"],
                actor_id="reviewer-1",
                role="reviewer",
                new_status="Under review",
                review_notes="Valid test note",
                changed_at=invalid_timestamp,
            )

    current = repo.get_observation(
        record["case_id"], actor_id="submitter-1", role="submitter"
    )
    events = repo.list_audit_events(
        record["case_id"], actor_id="admin-1", role="admin"
    )
    assert current["status"] == "Received"
    assert len(events) == 1

def test_status_update_rolls_back_when_audit_insert_fails(tmp_path):
    import sqlite3

    path = tmp_path / "pilot.sqlite3"
    repo = NemaAgoraRepository(path)
    record = repo.create_observation(
        sample_record(), actor_id="submitter-1", role="submitter"
    )
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_status_audit
            BEFORE INSERT ON audit_events
            WHEN NEW.event_type = 'status_changed'
            BEGIN
                SELECT RAISE(ABORT, 'simulated audit storage failure');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="simulated audit storage failure"):
        repo.update_review(
            record["case_id"],
            actor_id="reviewer-1",
            role="reviewer",
            new_status="Under review",
            review_notes="This update must roll back",
            changed_at="2026-10-04T12:10:00+03:00",
        )

    reopened = NemaAgoraRepository(path)
    current = reopened.get_observation(
        record["case_id"], actor_id="submitter-1", role="submitter"
    )
    events = reopened.list_audit_events(
        record["case_id"], actor_id="admin-1", role="admin"
    )
    assert current["status"] == "Received"
    assert current.get("review_notes", "") == ""
    assert len(events) == 1
    assert events[0]["event_type"] == "record_created"

def test_repository_ignores_caller_supplied_owner_and_validates_creation_timestamps(tmp_path):
    repo = NemaAgoraRepository(tmp_path / "pilot.sqlite3")
    record = sample_record()
    record["owner_id"] = "victim-2"
    created = repo.create_observation(
        record, actor_id="submitter-1", role="submitter"
    )
    assert created["owner_id"] == "submitter-1"
    with pytest.raises(PermissionError):
        repo.get_observation(
            created["case_id"], actor_id="victim-2", role="submitter"
        )

    invalid = sample_record()
    invalid["case_id"] = "NA-INVALID-TIME"
    invalid["created_at"] = "2026-10-04T12:00:00"
    with pytest.raises(ValueError, match="ISO 8601 timestamp with timezone"):
        repo.create_observation(
            invalid, actor_id="submitter-1", role="submitter"
        )
    assert repo.list_observations(
        actor_id="submitter-1", role="submitter"
    ) == [created]



def test_audit_and_operation_logs_are_append_only(tmp_path):
    import sqlite3

    path = tmp_path / "append-only.sqlite3"
    repo = NemaAgoraRepository(path)
    record = repo.create_observation(
        sample_record(), actor_id="submitter-1", role="submitter"
    )
    repo.record_intelligence_event(
        record["case_id"],
        actor_id="reviewer-1",
        role="reviewer",
        event_type="analysis_run",
        occurred_at="2026-10-04T12:01:00+03:00",
        details={"synthetic": True},
    )
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO operation_events(actor_id, operation, occurred_at, details_json) "
            "VALUES (?, ?, ?, ?)",
            ("admin-1", "health_check", "2026-10-04T12:02:00+03:00", "{}"),
        )

    statements = [
        ("UPDATE audit_events SET actor_id = 'tampered' WHERE case_id = ?", record["case_id"]),
        ("DELETE FROM audit_events WHERE case_id = ?", record["case_id"]),
        ("UPDATE operation_events SET operation = 'tampered'", None),
        ("DELETE FROM operation_events", None),
        ("UPDATE intelligence_events SET actor_id = 'tampered' WHERE case_id = ?", record["case_id"]),
        ("DELETE FROM intelligence_events WHERE case_id = ?", record["case_id"]),
    ]
    for statement, parameter in statements:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            with sqlite3.connect(path) as connection:
                if parameter is not None:
                    connection.execute(statement, (parameter,))
                else:
                    connection.execute(statement)


def test_read_fails_closed_when_record_payload_owner_drifts_from_indexed_owner(tmp_path):
    import json
    import sqlite3

    path = tmp_path / "payload-owner-drift.sqlite3"
    repository = NemaAgoraRepository(path)
    created = repository.create_observation(
        sample_record(), actor_id="integrity-owner", role="submitter"
    )
    tampered = dict(created)
    tampered["owner_id"] = "other-user"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE observations SET record_json = ? WHERE case_id = ?",
            (json.dumps(tampered, sort_keys=True), created["case_id"]),
        )

    with pytest.raises(ValueError, match="Stored observation integrity check failed"):
        repository.get_observation(
            created["case_id"], actor_id="integrity-owner", role="submitter"
        )
    with pytest.raises(ValueError, match="Stored observation integrity check failed"):
        repository.list_observations(
            actor_id="integrity-owner", role="submitter"
        )


def test_read_fails_closed_when_record_payload_status_drifts_from_indexed_status(tmp_path):
    import json
    import sqlite3

    path = tmp_path / "payload-status-drift.sqlite3"
    repository = NemaAgoraRepository(path)
    created = repository.create_observation(
        sample_record(), actor_id="integrity-status-owner", role="submitter"
    )
    tampered = dict(created)
    tampered["status"] = "Closed"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE observations SET record_json = ? WHERE case_id = ?",
            (json.dumps(tampered, sort_keys=True), created["case_id"]),
        )

    with pytest.raises(ValueError, match="Stored observation integrity check failed"):
        repository.get_observation(
            created["case_id"], actor_id="integrity-status-owner", role="submitter"
        )


def test_review_update_refuses_to_mutate_tampered_observation_payload(tmp_path):
    import json
    import sqlite3

    path = tmp_path / "tampered-review.sqlite3"
    repository = NemaAgoraRepository(path)
    created = repository.create_observation(
        sample_record(), actor_id="tampered-review-owner", role="submitter"
    )
    tampered = dict(created)
    tampered["owner_id"] = "forged-owner"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE observations SET record_json = ? WHERE case_id = ?",
            (json.dumps(tampered, sort_keys=True), created["case_id"]),
        )

    with pytest.raises(ValueError, match="Stored observation integrity check failed"):
        repository.update_review(
            created["case_id"], actor_id="integrity-reviewer", role="reviewer",
            new_status="Under review", review_notes="Should not apply",
            changed_at="2026-10-04T12:10:00+03:00",
        )

    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT status FROM observations WHERE case_id = ?",
            (created["case_id"],),
        ).fetchone()
        event_count = connection.execute(
            "SELECT COUNT(*) FROM audit_events WHERE case_id = ?",
            (created["case_id"],),
        ).fetchone()[0]
    assert row[0] == "Received"
    assert event_count == 1

def test_legacy_records_migrate_to_unowned_without_trusting_payload_owner(tmp_path):
    import json
    import sqlite3

    path = tmp_path / "legacy-observations.sqlite3"
    legacy = sample_record()
    legacy["updated_at"] = legacy["created_at"]
    legacy["owner_id"] = "untrusted-legacy-owner"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TABLE observations (
                case_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                record_json TEXT NOT NULL
            )"""
        )
        connection.execute(
            """INSERT INTO observations
               (case_id, status, created_at, updated_at, record_json)
               VALUES (?, ?, ?, ?, ?)""",
            (
                legacy["case_id"],
                legacy["status"],
                legacy["created_at"],
                legacy["updated_at"],
                json.dumps(legacy, sort_keys=True),
            ),
        )

    repository = NemaAgoraRepository(path)
    migrated = repository.get_observation(
        legacy["case_id"], actor_id="migration-reviewer", role="admin"
    )
    assert migrated["owner_id"] == "legacy-unowned"
    with pytest.raises(PermissionError):
        repository.get_observation(
            legacy["case_id"], actor_id="untrusted-legacy-owner", role="submitter"
        )

def test_complete_case_lifecycle_keeps_status_and_audit_history_in_sync(tmp_path):
    repository = NemaAgoraRepository(tmp_path / "case-lifecycle.sqlite3")
    created = repository.create_observation(
        sample_record(), actor_id="lifecycle-submitter", role="submitter"
    )
    transitions = [
        ("Under review", "2026-10-04T12:10:00+03:00"),
        ("Referred", "2026-10-04T12:20:00+03:00"),
        ("Action recorded", "2026-10-04T12:30:00+03:00"),
        ("Closed", "2026-10-04T12:40:00+03:00"),
        ("Under review", "2026-10-04T12:50:00+03:00"),
    ]

    for index, (new_status, changed_at) in enumerate(transitions):
        updated = repository.update_review(
            created["case_id"],
            actor_id="lifecycle-reviewer",
            role="reviewer",
            new_status=new_status,
            review_notes=f"Lifecycle step {index + 1}",
            changed_at=changed_at,
        )
        assert updated["status"] == new_status
        assert updated["updated_at"] == changed_at

    persisted = repository.get_observation(
        created["case_id"], actor_id="lifecycle-submitter", role="submitter"
    )
    events = repository.list_audit_events(
        created["case_id"], actor_id="lifecycle-admin", role="admin"
    )

    assert persisted["status"] == "Under review"
    assert persisted["review_notes"] == "Lifecycle step 5"
    assert [event["event_type"] for event in events] == [
        "record_created",
        "status_changed",
        "status_changed",
        "status_changed",
        "status_changed",
        "status_changed",
    ]
    assert [(event["from_status"], event["to_status"]) for event in events[1:]] == [
        ("Received", "Under review"),
        ("Under review", "Referred"),
        ("Referred", "Action recorded"),
        ("Action recorded", "Closed"),
        ("Closed", "Under review"),
    ]
    assert [event["occurred_at"] for event in events] == [
        created["created_at"],
        *(changed_at for _, changed_at in transitions),
    ]


def test_review_notes_only_update_is_audited_without_fake_status_transition(tmp_path):
    repository = NemaAgoraRepository(tmp_path / "review-note-only.sqlite3")
    created = repository.create_observation(
        sample_record(), actor_id="notes-submitter", role="submitter"
    )
    reviewed = repository.update_review(
        created["case_id"],
        actor_id="notes-reviewer",
        role="reviewer",
        new_status="Received",
        review_notes="Clarified intake details",
        changed_at="2026-10-04T12:10:00+03:00",
    )
    events = repository.list_audit_events(
        created["case_id"], actor_id="notes-admin", role="admin"
    )

    assert reviewed["status"] == "Received"
    assert reviewed["review_notes"] == "Clarified intake details"
    assert len(events) == 2
    assert events[-1]["event_type"] == "review_updated"
    assert events[-1]["from_status"] is None
    assert events[-1]["to_status"] == "Received"

def test_legacy_malformed_payload_is_preserved_and_rejected_after_migration(tmp_path):
    import sqlite3

    path = tmp_path / "legacy-malformed.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """CREATE TABLE observations (
                case_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                record_json TEXT NOT NULL
            )"""
        )
        connection.execute(
            """INSERT INTO observations
               (case_id, status, created_at, updated_at, record_json)
               VALUES (?, ?, ?, ?, ?)""",
            (
                "NA-LEGACY-BROKEN",
                "Received",
                "2026-10-04T12:00:00+03:00",
                "2026-10-04T12:00:00+03:00",
                "{malformed-json",
            ),
        )

    repository = NemaAgoraRepository(path)
    with pytest.raises(ValueError, match="Stored observation integrity check failed"):
        repository.get_observation(
            "NA-LEGACY-BROKEN", actor_id="migration-admin", role="admin"
        )

    with sqlite3.connect(path) as connection:
        stored_payload = connection.execute(
            "SELECT record_json FROM observations WHERE case_id = ?",
            ("NA-LEGACY-BROKEN",),
        ).fetchone()[0]
    assert stored_payload == "{malformed-json"

