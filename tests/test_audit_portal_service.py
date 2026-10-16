"""Tests for fail-closed portal configuration and persistent submission workflow."""
from __future__ import annotations

import ast
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
