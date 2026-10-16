"""Tests for fail-closed portal configuration and persistent submission workflow."""
from __future__ import annotations

import ast
import sqlite3
from pathlib import Path

import pytest

from modules import audit_portal
from modules.audit_portal_service import (
    PortalConfigurationError,
    is_professor_session_valid,
    load_portal_credentials,
    verify_professor_password,
)


def test_streamlit_secrets_take_precedence_over_environment():
    encryption, professor = load_portal_credentials(
        {
            "AUDIT_PORTAL_ENCRYPTION_PASSWORD": "secret-encryption-key",
            "AUDIT_PORTAL_PROFESSOR_PASSWORD": "secret-professor-key",
        },
        {
            "AUDIT_PORTAL_ENCRYPTION_PASSWORD": "environment-encryption-key",
            "AUDIT_PORTAL_PROFESSOR_PASSWORD": "environment-professor-key",
        },
    )
    assert encryption == "secret-encryption-key"
    assert professor == "secret-professor-key"


def test_environment_can_supply_both_required_secrets():
    encryption, professor = load_portal_credentials(
        {},
        {
            "AUDIT_PORTAL_ENCRYPTION_PASSWORD": "environment-encryption-key",
            "AUDIT_PORTAL_PROFESSOR_PASSWORD": "environment-professor-key",
        },
    )
    assert encryption == "environment-encryption-key"
    assert professor == "environment-professor-key"


def test_missing_secrets_fail_closed_without_builtin_defaults():
    with pytest.raises(PortalConfigurationError) as error:
        load_portal_credentials({}, {})
    assert "AUDIT_PORTAL_ENCRYPTION_PASSWORD" in str(error.value)
    assert "AUDIT_PORTAL_PROFESSOR_PASSWORD" in str(error.value)


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_configured_secrets_are_rejected(value):
    with pytest.raises(PortalConfigurationError):
        load_portal_credentials(
            {
                "AUDIT_PORTAL_ENCRYPTION_PASSWORD": value,
                "AUDIT_PORTAL_PROFESSOR_PASSWORD": "professor-key",
            },
            {},
        )


def test_professor_password_comparison_rejects_blank_and_wrong_values():
    assert verify_professor_password("correct", "correct") is True
    assert verify_professor_password("wrong", "correct") is False
    assert verify_professor_password("", "correct") is False
    assert verify_professor_password("correct", "") is False


@pytest.mark.skipif(not audit_portal.HAS_CRYPTOGRAPHY, reason="cryptography package unavailable")
def test_configured_key_supports_persistent_submit_decrypt_and_review(tmp_path):
    encryption, _professor = load_portal_credentials(
        {
            "AUDIT_PORTAL_ENCRYPTION_PASSWORD": "a-strong-encryption-test-key",
            "AUDIT_PORTAL_PROFESSOR_PASSWORD": "a-different-professor-test-key",
        },
        {},
    )
    database_path = tmp_path / "portal.sqlite3"
    system = audit_portal.CHRISHEMSubmissionSystem(database_path)
    research_content = "Dissolved oxygen measurements and interpretation."
    result = system.submit(
        7,
        "Researcher One",
        "Water quality analysis",
        research_content,
        password=encryption,
        student_email="researcher@example.test",
    )

    # Re-open through a fresh instance to exercise persistence across app-object restart.
    reopened = audit_portal.CHRISHEMSubmissionSystem(database_path)
    stored_before_review = reopened.get_submission(result["id"])
    assert stored_before_review["encrypted_content"] != research_content
    assert research_content not in stored_before_review["encrypted_content"]
    assert reopened.decrypt_submission(result["id"], encryption) == research_content

    assert reopened.review(
        result["id"],
        "A",
        92.0,
        "Clear methods and sound interpretation.",
        professor_password=encryption,
    )
    reopened_again = audit_portal.CHRISHEMSubmissionSystem(database_path)
    saved = reopened_again.get_submission(result["id"])
    assert saved["status"] == "reviewed"
    assert saved["professor_score"] == 92.0
    assert saved["professor_feedback"] != "Clear methods and sound interpretation."
    assert "Clear methods and sound interpretation." not in saved["professor_feedback"]
    assert audit_portal.decrypt_text(saved["professor_feedback"], encryption) == (
        "Clear methods and sound interpretation."
    )


def test_streamlit_page_is_valid_python():
    page = Path("pages/18_Research_Submission_Portal.py")
    ast.parse(page.read_text(encoding="utf-8"), filename=str(page))


@pytest.mark.parametrize(
    ("authenticated", "authenticated_at", "now", "expected"),
    [
        (True, 100.0, 100.0, True),
        (True, 100.0, 999.0, True),
        (True, 100.0, 1000.0, False),
        (True, None, 100.0, False),
        (False, 100.0, 100.0, False),
        (True, 101.0, 100.0, False),
        (True, True, 100.0, False),
    ],
)
def test_professor_session_has_a_bounded_lifetime(
    authenticated, authenticated_at, now, expected
):
    assert is_professor_session_valid(
        authenticated, authenticated_at, now=now
    ) is expected


@pytest.mark.skipif(not audit_portal.HAS_CRYPTOGRAPHY, reason="cryptography package unavailable")
def test_review_methods_report_missing_submission_ids(tmp_path):
    system = audit_portal.CHRISHEMSubmissionSystem(tmp_path / "portal.sqlite3")

    assert system.review(
        999999,
        "A",
        90.0,
        "This review must not be recorded.",
        professor_password="a-strong-test-password",
    ) is False
    assert system.return_for_revision(
        999999,
        "This revision request must not be recorded.",
        professor_password="a-strong-test-password",
    ) is False


@pytest.mark.parametrize("grade", ["", "   ", None])
def test_review_rejects_blank_grade_before_database_update(tmp_path, grade):
    system = audit_portal.CHRISHEMSubmissionSystem(tmp_path / "portal.sqlite3")
    with pytest.raises(ValueError, match="non-empty grade"):
        system.review(1, grade, 90.0, "Useful feedback", professor_password="test-password")


@pytest.mark.parametrize("score", [-1, 101, float("nan"), float("inf"), True, "90"])
def test_review_rejects_invalid_score_before_database_update(tmp_path, score):
    system = audit_portal.CHRISHEMSubmissionSystem(tmp_path / "portal.sqlite3")
    with pytest.raises(ValueError, match="finite number between 0 and 100"):
        system.review(1, "A", score, "Useful feedback", professor_password="test-password")


@pytest.mark.parametrize("feedback", ["", "   ", None])
def test_review_rejects_blank_feedback_before_database_update(tmp_path, feedback):
    system = audit_portal.CHRISHEMSubmissionSystem(tmp_path / "portal.sqlite3")
    with pytest.raises(ValueError, match="Non-empty review feedback"):
        system.review(1, "A", 90.0, feedback, professor_password="test-password")


@pytest.mark.parametrize("feedback", ["", "   ", None])
def test_return_for_revision_rejects_blank_feedback(tmp_path, feedback):
    system = audit_portal.CHRISHEMSubmissionSystem(tmp_path / "portal.sqlite3")
    with pytest.raises(ValueError, match="Non-empty revision feedback"):
        system.return_for_revision(1, feedback, professor_password="test-password")


@pytest.mark.skipif(not audit_portal.HAS_CRYPTOGRAPHY, reason="cryptography package unavailable")
def test_submission_event_history_is_persistent_and_excludes_feedback_text(tmp_path):
    database_path = tmp_path / "portal-events.sqlite3"
    system = audit_portal.CHRISHEMSubmissionSystem(database_path)
    result = system.submit(
        4,
        "Researcher Event Test",
        "Synthetic submission",
        "Synthetic research content",
        password="event-test-encryption-key",
    )
    submission_id = result["id"]

    events = system.get_submission_events(submission_id)
    assert len(events) == 1
    assert events[0]["event_type"] == "submission_created"
    assert events[0]["previous_status"] is None
    assert events[0]["new_status"] == "submitted"

    private_feedback = "CONFIDENTIAL-FEEDBACK-MUST-NOT-ENTER-EVENTS"
    assert system.review(
        submission_id,
        "A",
        91.0,
        private_feedback,
        professor_password="event-test-encryption-key",
    )
    assert system.return_for_revision(
        submission_id,
        "Second synthetic revision note",
        professor_password="event-test-encryption-key",
    )

    reopened = audit_portal.CHRISHEMSubmissionSystem(database_path)
    events = reopened.get_submission_events(submission_id)
    assert [event["event_type"] for event in events] == [
        "submission_created",
        "review_saved",
        "returned_for_revision",
    ]
    assert [(event["previous_status"], event["new_status"]) for event in events] == [
        (None, "submitted"),
        ("submitted", "reviewed"),
        ("reviewed", "returned"),
    ]
    assert all(private_feedback not in event["details_json"] for event in events)


@pytest.mark.skipif(not audit_portal.HAS_CRYPTOGRAPHY, reason="cryptography package unavailable")
def test_event_table_migration_preserves_existing_submission_rows(tmp_path):
    database_path = tmp_path / "legacy-portal.sqlite3"
    encryption_password = "migration-test-encryption-key"
    initial = audit_portal.CHRISHEMSubmissionSystem(database_path)
    submitted = initial.submit(
        12,
        "Legacy Researcher",
        "Existing record before event migration",
        "Keep this original synthetic research record.",
        password=encryption_password,
    )
    with sqlite3.connect(database_path) as conn:
        conn.execute("DROP TABLE portal_audit_events")
        conn.commit()

    # Initialization should add the event table without rebuilding or dropping
    # the existing submission table and its encrypted record.
    migrated = audit_portal.CHRISHEMSubmissionSystem(database_path)
    existing = migrated.get_submission(submitted["id"])
    assert existing["title"] == "Existing record before event migration"
    assert migrated.decrypt_submission(submitted["id"], encryption_password) == (
        "Keep this original synthetic research record."
    )
    assert migrated.get_submission_events(submitted["id"]) == []
    with sqlite3.connect(database_path) as conn:
        table_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert "portal_submissions" in table_names
    assert "portal_audit_events" in table_names


@pytest.mark.skipif(not audit_portal.HAS_CRYPTOGRAPHY, reason="cryptography package unavailable")
def test_submission_and_event_are_atomic_when_event_insert_fails(tmp_path):
    database_path = tmp_path / "portal-atomicity.sqlite3"
    system = audit_portal.CHRISHEMSubmissionSystem(database_path)
    with sqlite3.connect(database_path) as conn:
        conn.execute(
            """CREATE TRIGGER reject_portal_event
               BEFORE INSERT ON portal_audit_events
               BEGIN SELECT RAISE(ABORT, 'simulated event-store failure'); END"""
        )
        conn.commit()

    with pytest.raises(sqlite3.IntegrityError, match="simulated event-store failure"):
        system.submit(
            3,
            "Atomicity Researcher",
            "Must not be partially saved",
            "Synthetic test content",
            password="atomicity-test-encryption-key",
        )

    with sqlite3.connect(database_path) as conn:
        submission_count = conn.execute(
            "SELECT COUNT(*) FROM portal_submissions"
        ).fetchone()[0]
        event_count = conn.execute(
            "SELECT COUNT(*) FROM portal_audit_events"
        ).fetchone()[0]
    assert submission_count == 0
    assert event_count == 0


def test_encryption_and_professor_access_secrets_must_be_distinct():
    shared = "same-test-secret"
    with pytest.raises(PortalConfigurationError, match="must be different"):
        load_portal_credentials(
            {
                "AUDIT_PORTAL_ENCRYPTION_PASSWORD": shared,
                "AUDIT_PORTAL_PROFESSOR_PASSWORD": shared,
            },
            {},
        )


@pytest.mark.skipif(not audit_portal.HAS_CRYPTOGRAPHY, reason="cryptography package unavailable")
@pytest.mark.parametrize("decision", ["review", "return"])
def test_review_decision_and_event_are_atomic_when_event_insert_fails(tmp_path, decision):
    database_path = tmp_path / f"decision-atomicity-{decision}.sqlite3"
    encryption_password = "atomicity-encryption-test-key"
    system = audit_portal.CHRISHEMSubmissionSystem(database_path)
    result = system.submit(
        5,
        "Atomic Decision Researcher",
        "Atomic decision test",
        "Synthetic research content",
        password=encryption_password,
    )
    submission_id = result["id"]
    rejected_event = "review_saved" if decision == "review" else "returned_for_revision"

    with sqlite3.connect(database_path) as conn:
        conn.execute(
            f"""CREATE TRIGGER reject_decision_event
                BEFORE INSERT ON portal_audit_events
                WHEN NEW.event_type = '{rejected_event}'
                BEGIN SELECT RAISE(ABORT, 'simulated decision event failure'); END"""
        )
        conn.commit()

    with pytest.raises(sqlite3.IntegrityError, match="simulated decision event failure"):
        if decision == "review":
            system.review(
                submission_id,
                "A",
                95.0,
                "Synthetic feedback that must not be partially saved.",
                professor_password=encryption_password,
            )
        else:
            system.return_for_revision(
                submission_id,
                "Synthetic revision feedback that must not be partially saved.",
                professor_password=encryption_password,
            )

    persisted = system.get_submission(submission_id)
    assert persisted["status"] == "submitted"
    assert persisted["professor_grade"] is None
    assert persisted["professor_score"] is None
    assert persisted["professor_feedback"] is None
    events = system.get_submission_events(submission_id)
    assert [event["event_type"] for event in events] == ["submission_created"]
