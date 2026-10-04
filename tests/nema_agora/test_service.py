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
