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
    system = audit_portal.CHRISHEMSubmissionSystem(tmp_path / "portal.sqlite3")
    result = system.submit(
        7,
        "Researcher One",
        "Water quality analysis",
        "Dissolved oxygen measurements and interpretation.",
        password=encryption,
        student_email="researcher@example.test",
    )
    assert system.decrypt_submission(result["id"], encryption) == (
        "Dissolved oxygen measurements and interpretation."
    )

    assert system.review(
        result["id"],
        "A",
        92.0,
        "Clear methods and sound interpretation.",
        professor_password=encryption,
    )
    saved = system.get_submission(result["id"])
    assert saved["status"] == "reviewed"
    assert saved["professor_score"] == 92.0
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
