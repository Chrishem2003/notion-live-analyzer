"""Integrated pilot workflow across identity, service, persistence, audit and recovery."""
from datetime import date, datetime, timezone

from nema_agora.backup import backup_database, integrity_check, restore_database
from nema_agora.core import CATEGORIES, make_observation
from nema_agora.identity import Principal
from nema_agora.service import NemaAgoraService
from nema_agora.storage import NemaAgoraRepository


def principal(subject: str, role: str) -> Principal:
    return Principal(
        subject_key=f"https://issuer.example.test|{subject}",
        issuer="https://issuer.example.test",
        subject=subject,
        role=role,
    )


def sample_record() -> dict:
    return make_observation(
        observation_date=date(2026, 10, 10),
        category=CATEGORIES[0],
        severity="Moderate",
        site="Synthetic pilot site",
        description="Synthetic end-to-end test record; not a real incident.",
        latitude=2.5,
        longitude=32.1,
        consent_confirmed=True,
        created_at="2026-10-10T10:00:00+03:00",
    )


def test_pilot_record_review_audit_backup_restore_journey(tmp_path):
    database = tmp_path / "nema_agora.sqlite3"
    backup_dir = tmp_path / "backups"
    submitter = principal("submitter-1", "submitter")
    reviewer = principal("reviewer-1", "reviewer")
    admin = principal("admin-1", "admin")
    service = NemaAgoraService(NemaAgoraRepository(database))

    created = service.create_observation(sample_record(), submitter)
    assert created["owner_id"] == submitter.subject_key
    assert service.get_observation(created["case_id"], submitter) == created

    reviewed = service.update_review(
        created["case_id"], reviewer,
        new_status="Under review",
        review_notes="Synthetic end-to-end triage",
        changed_at="2026-10-10T10:05:00+03:00",
    )
    assert reviewed["status"] == "Under review"
    assert service.get_observation(created["case_id"], submitter)["status"] == "Under review"

    events = service.list_audit_events(created["case_id"], admin)
    assert [event["event_type"] for event in events] == ["record_created", "status_changed"]
    assert events[0]["actor_id"] == submitter.subject_key
    assert events[1]["actor_id"] == reviewer.subject_key

    backup = backup_database(
        database, backup_dir,
        now=datetime(2026, 10, 10, 7, 0, tzinfo=timezone.utc),
    )
    assert integrity_check(backup)

    restored_database = tmp_path / "restored.sqlite3"
    restore_database(backup, restored_database, confirm_destructive=True)
    restored_service = NemaAgoraService(NemaAgoraRepository(restored_database))
    restored = restored_service.get_observation(created["case_id"], admin)
    assert restored is not None
    assert restored["status"] == "Under review"
    restored_events = restored_service.list_audit_events(created["case_id"], admin)
    assert restored_events == events
