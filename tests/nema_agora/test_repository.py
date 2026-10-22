from __future__ import annotations

import pytest

from nema_agora.repository import (
    CaseNotFoundError,
    ConcurrentCaseUpdateError,
    NemaCaseRepository,
)


def _record(case_id: str = "NA-TEST1234") -> dict:
    return {
        "case_id": case_id,
        "status": "Received",
        "district_or_site": "Gulu",
        "category": "Water pollution",
        "severity": "Moderate",
        "description": "Illustrative observation for repository tests.",
        "observation_date": "2026-10-22",
    }


@pytest.fixture
def repository():
    repo = NemaCaseRepository(":memory:")
    yield repo
    repo.close()


def test_create_case_persists_record_and_creation_audit(repository):
    original = _record()
    saved, version = repository.create_case(
        original, actor="test-operator", created_at="2026-10-22T10:00:00+03:00"
    )

    assert version == 1
    assert saved == original
    assert repository.get_case("NA-TEST1234") == (original, 1)
    events = repository.list_audit_events("NA-TEST1234")
    assert len(events) == 1
    assert events[0]["event_type"] == "case_created"
    assert events[0]["actor"] == "test-operator"


def test_duplicate_case_id_is_rejected_without_extra_audit(repository):
    repository.create_case(_record(), actor="operator", created_at="2026-10-22T07:00:00Z")
    with pytest.raises(ValueError, match="already exists"):
        repository.create_case(_record(), actor="operator", created_at="2026-10-22T07:01:00Z")
    assert len(repository.list_audit_events("NA-TEST1234")) == 1


def test_transition_updates_record_and_audit_atomically(repository):
    original = _record()
    repository.create_case(original, actor="operator", created_at="2026-10-22T07:00:00Z")

    updated, event, version = repository.transition_case(
        "NA-TEST1234",
        new_status="Under review",
        actor="reviewer-1",
        changed_at="2026-10-22T07:05:00Z",
        expected_version=1,
    )

    assert updated["status"] == "Under review"
    assert original["status"] == "Received"
    assert event["from_status"] == "Received"
    assert event["to_status"] == "Under review"
    assert event["version_before"] == 1
    assert event["version_after"] == 2
    assert version == 2
    assert repository.get_case("NA-TEST1234") == (updated, 2)
    assert len(repository.list_audit_events("NA-TEST1234")) == 2


def test_stale_version_is_rejected_and_does_not_write_audit(repository):
    repository.create_case(_record(), actor="operator", created_at="2026-10-22T07:00:00Z")
    repository.transition_case(
        "NA-TEST1234", new_status="Under review", actor="reviewer",
        changed_at="2026-10-22T07:05:00Z", expected_version=1,
    )

    with pytest.raises(ConcurrentCaseUpdateError, match="Stale"):
        repository.transition_case(
            "NA-TEST1234", new_status="Closed", actor="reviewer",
            changed_at="2026-10-22T07:06:00Z", expected_version=1,
        )
    assert len(repository.list_audit_events("NA-TEST1234")) == 2
    assert repository.get_case("NA-TEST1234")[1] == 2


def test_invalid_transition_rolls_back_without_audit(repository):
    repository.create_case(_record(), actor="operator", created_at="2026-10-22T07:00:00Z")
    with pytest.raises(ValueError, match="not allowed"):
        repository.transition_case(
            "NA-TEST1234", new_status="Closed", actor="reviewer",
            changed_at="2026-10-22T07:05:00Z", expected_version=1,
        )
    assert repository.get_case("NA-TEST1234") == (_record(), 1)
    assert len(repository.list_audit_events("NA-TEST1234")) == 1


def test_reopening_closed_case_requires_reason(repository):
    record = _record()
    record["status"] = "Closed"
    repository.create_case(record, actor="operator", created_at="2026-10-22T07:00:00Z")
    with pytest.raises(ValueError, match="reason"):
        repository.transition_case(
            "NA-TEST1234", new_status="Under review", actor="reviewer",
            changed_at="2026-10-22T07:05:00Z", expected_version=1,
        )
    updated, event, version = repository.transition_case(
        "NA-TEST1234", new_status="Under review", actor="reviewer",
        changed_at="2026-10-22T07:06:00Z", expected_version=1,
        reason="New evidence was submitted for reassessment.",
    )
    assert updated["status"] == "Under review"
    assert event["reason"] == "New evidence was submitted for reassessment."
    assert version == 2


def test_missing_case_and_invalid_timestamp_fail_closed(repository):
    with pytest.raises(CaseNotFoundError):
        repository.transition_case(
            "missing", new_status="Under review", actor="reviewer",
            changed_at="2026-10-22T07:05:00Z", expected_version=1,
        )
    with pytest.raises(ValueError, match="timezone"):
        repository.create_case(_record(), actor="operator", created_at="2026-10-22T07:00:00")
    assert repository.get_case("NA-TEST1234") is None


def test_limit_validation_rejects_bool(repository):
    with pytest.raises(ValueError):
        repository.list_cases(limit=True)
    with pytest.raises(ValueError):
        repository.list_audit_events("NA-TEST1234", limit=0)



def test_audit_events_are_protected_from_update_and_delete(repository):
    repository.create_case(_record(), actor="operator", created_at="2026-10-22T07:00:00Z")
    with pytest.raises(Exception, match="append-only"):
        repository._connection.execute(
            "UPDATE nema_case_audit SET event_type = 'rewritten' WHERE case_id = ?",
            ("NA-TEST1234",),
        )
    with pytest.raises(Exception, match="append-only"):
        repository._connection.execute(
            "DELETE FROM nema_case_audit WHERE case_id = ?",
            ("NA-TEST1234",),
        )
    assert len(repository.list_audit_events("NA-TEST1234")) == 1


def test_file_backed_case_and_audit_survive_repository_reopen(tmp_path):
    database = tmp_path / "nema" / "cases.sqlite3"
    first = NemaCaseRepository(database)
    first.create_case(_record(), actor="operator", created_at="2026-10-22T07:00:00Z")
    first.transition_case(
        "NA-TEST1234", new_status="Under review", actor="reviewer",
        changed_at="2026-10-22T07:05:00Z", expected_version=1,
    )
    first.close()

    second = NemaCaseRepository(database)
    try:
        record, version = second.get_case("NA-TEST1234")
        assert record["status"] == "Under review"
        assert version == 2
        assert len(second.list_audit_events("NA-TEST1234")) == 2
    finally:
        second.close()
