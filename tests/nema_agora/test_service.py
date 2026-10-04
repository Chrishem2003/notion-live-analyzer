from datetime import date

import pytest

from nema_agora.core import CATEGORIES, make_observation
from nema_agora.identity import Principal
from nema_agora.service import NemaAgoraService
from nema_agora.storage import NemaAgoraRepository


def principal(subject: str, role: str | None) -> Principal:
    return Principal(
        subject_key=f"https://issuer|{subject}",
        issuer="https://issuer",
        subject=subject,
        role=role,
    )


def record():
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


def test_service_uses_principal_for_creation_and_read(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    created = service.create_observation(record(), principal("submitter-1", "submitter"))
    assert service.get_observation(created["case_id"], principal("submitter-1", "submitter")) == created
    with pytest.raises(PermissionError):
        service.get_observation(created["case_id"], principal("submitter-2", "submitter"))


def test_unprovisioned_principal_cannot_touch_repository(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    with pytest.raises(PermissionError):
        service.create_observation(record(), principal("unknown", None))


def test_submitter_cannot_export(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    with pytest.raises(PermissionError):
        service.export_csv(principal("submitter-1", "submitter"), [record()])


def test_coordinator_can_export(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    data = service.export_csv(principal("coord-1", "coordinator"), [record()])
    assert data.startswith(b"\xef\xbb\xbf")
    assert b"case_id" in data


def test_admin_operation_audit_is_principal_bound(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    admin = principal("admin-1", "admin")
    service.record_operation(admin, operation="backup_created", occurred_at="2026-10-04T12:00:00+03:00", details={"backup": "x.sqlite3"})
    events = service.list_operation_events(admin)
    assert events[0]["operation"] == "backup_created"
    assert events[0]["actor_id"] == "https://issuer|admin-1"
    with pytest.raises(PermissionError):
        service.record_operation(principal("coord-1", "coordinator"), operation="backup_created", occurred_at="now")


def test_service_cannot_accept_caller_supplied_owner_id(tmp_path):
    repo = NemaAgoraRepository(tmp_path / "pilot.sqlite3")
    service = NemaAgoraService(repo)
    owner = principal("owner-1", "submitter")
    record = make_observation(
        observation_date=date(2026, 10, 4), category=CATEGORIES[0], severity="Low",
        site="Pilot A", description="Synthetic", latitude=2.5, longitude=32.1,
        consent_confirmed=True, created_at="2026-10-04T12:00:00+03:00",
    )
    record["owner_id"] = "attacker-2"
    service.create_observation(record, owner)
    assert repo.get_observation(record["case_id"], actor_id=owner.subject_key, role="submitter")["owner_id"] == owner.subject_key


def test_intelligence_requires_reviewer_permission(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    owner = principal("submitter-1", "submitter")
    reviewer = principal("reviewer-1", "reviewer")
    rec = record()
    with pytest.raises(PermissionError):
        service.analyze_observation(rec, owner)
    result = service.analyze_observation(rec, reviewer, peer_records=[])
    assert result["human_review_required"] is True


def test_reviewer_copilot_and_feedback_are_principal_bound(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    reviewer = principal("reviewer-1", "reviewer")
    rec = service.create_observation(record(), principal("submitter-1", "submitter"))
    copilot = service.build_reviewer_copilot(rec, reviewer, peer_records=[rec])
    assert copilot["source_case_id"] == rec["case_id"]
    service.record_intelligence_feedback(
        rec["case_id"],
        reviewer,
        feedback={
            "feedback_type": "accepted",
            "copilot_version": copilot["copilot_version"],
            "notes": "Synthetic reviewer feedback",
        },
        occurred_at="2026-10-04T12:05:00+03:00",
    )
    events = service.list_intelligence_events(rec["case_id"], principal("admin-1", "admin"))
    assert [e["event_type"] for e in events] == ["analysis_run", "feedback_recorded"]


def test_submitter_cannot_record_copilot_feedback(tmp_path):
    service = NemaAgoraService(NemaAgoraRepository(tmp_path / "pilot.sqlite3"))
    rec = service.create_observation(record(), principal("submitter-1", "submitter"))
    with pytest.raises(PermissionError):
        service.record_intelligence_feedback(
            rec["case_id"], principal("submitter-1", "submitter"),
            feedback={"feedback_type": "accepted"},
            occurred_at="2026-10-04T12:05:00+03:00",
        )
