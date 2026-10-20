"""End-to-end persistent journey through the principal-bound NEMA service.

Uses a temporary SQLite file and synthetic records only; this is not a
substitute for a deployment-backed authentication and storage test.
"""
from datetime import date

from nema_agora.core import CATEGORIES, make_observation
from nema_agora.identity import Principal
from nema_agora.runtime import initialize_persistent_service


def _principal(subject: str, role: str) -> Principal:
    return Principal(
        subject_key=f"https://issuer.example|{subject}",
        issuer="https://issuer.example",
        subject=subject,
        role=role,
        email=f"{subject}@example.test",
        display_name=subject,
    )


def _record() -> dict:
    return make_observation(
        observation_date=date(2026, 10, 18),
        category=CATEGORIES[0],
        severity="Moderate",
        site="Synthetic Pilot Site",
        description="Synthetic end-to-end persistence verification record",
        latitude=2.5,
        longitude=32.1,
        consent_confirmed=True,
        created_at="2026-10-18T12:00:00+03:00",
    )


def test_persistent_create_read_review_and_audit_journey(tmp_path):
    database_path = tmp_path / "nema-pilot.sqlite3"
    submitter = _principal("submitter-01", "submitter")
    reviewer = _principal("reviewer-01", "reviewer")
    auditor = _principal("auditor-01", "admin")

    service = initialize_persistent_service(database_path)
    created = service.create_observation(_record(), submitter)
    assert created["owner_id"] == submitter.subject_key
    assert created["status"] == "Received"

    # Re-open the persistent database through a fresh service/repository instance.
    reopened = initialize_persistent_service(database_path)
    read_back = reopened.get_observation(created["case_id"], submitter)
    assert read_back == created

    reviewed = reopened.update_review(
        created["case_id"],
        reviewer,
        new_status="Under review",
        review_notes="Synthetic verification; no environmental conclusion.",
        changed_at="2026-10-18T12:10:00+03:00",
    )
    assert reviewed["status"] == "Under review"

    events = reopened.list_audit_events(created["case_id"], auditor)
    assert [event["event_type"] for event in events] == [
        "record_created",
        "status_changed",
    ]
    assert [event["actor_id"] for event in events] == [
        submitter.subject_key,
        reviewer.subject_key,
    ]
    assert events[-1]["to_status"] == "Under review"


def test_unprovisioned_principal_cannot_start_persistent_journey(tmp_path):
    import pytest

    service = initialize_persistent_service(tmp_path / "nema-pilot.sqlite3")
    unprovisioned = _principal("not-provisioned", "not-a-real-role")

    with pytest.raises(PermissionError, match="not provisioned"):
        service.create_observation(_record(), unprovisioned)
