"""Focused regression tests for the encrypted audit submission portal.

All database writes use isolated temporary SQLite files; no repository/demo DB is touched.
"""
from __future__ import annotations

import importlib
import sys
import types

import pytest

# The submission engine does not need Streamlit's UI or plotting stack.
# Stub those optional UI imports so tests stay focused and lightweight.
for _name in ("plotly", "plotly.express", "plotly.graph_objects", "plotly.subplots", "streamlit"):
    if _name not in sys.modules:
        _module = types.ModuleType(_name)
        if _name == "plotly":
            _module.__path__ = []
        if _name == "plotly.subplots":
            _module.make_subplots = lambda *args, **kwargs: None
        sys.modules[_name] = _module

audit_portal = importlib.import_module("modules.audit_portal")
CHRISHEMSubmissionSystem = audit_portal.CHRISHEMSubmissionSystem


@pytest.fixture
def portal(tmp_path):
    return CHRISHEMSubmissionSystem(tmp_path / "portal-test.sqlite3")


def test_encryption_round_trip_and_random_salt():
    first = audit_portal.encrypt_text("sensitive research submission", "correct horse")
    second = audit_portal.encrypt_text("sensitive research submission", "correct horse")

    assert first.startswith("v2:")
    assert second.startswith("v2:")
    assert first != second
    assert audit_portal.decrypt_text(first, "correct horse") == "sensitive research submission"
    assert audit_portal.decrypt_text(second, "correct horse") == "sensitive research submission"


def test_legacy_encrypted_records_remain_readable():
    legacy_key = audit_portal.derive_fernet_key("legacy-password", audit_portal.LEGACY_SALT)
    legacy_token = audit_portal.Fernet(legacy_key).encrypt(b"legacy submission")

    assert audit_portal.decrypt_text(legacy_token.decode(), "legacy-password") == "legacy submission"


def test_wrong_password_does_not_return_plaintext():
    token = audit_portal.encrypt_text("private answer", "right-password")

    result = audit_portal.decrypt_text(token, "wrong-password")

    assert isinstance(result, str)
    assert "private answer" not in result
    assert "Decryption failed" in result


def test_encryption_fails_closed_when_cryptography_is_unavailable(monkeypatch):
    monkeypatch.setattr(audit_portal, "HAS_CRYPTOGRAPHY", False)
    monkeypatch.setattr(audit_portal, "Fernet", None)

    with pytest.raises(audit_portal.CryptographyUnavailable):
        audit_portal.encrypt_text("must not be stored as plaintext", "password")


def test_submit_persists_only_encrypted_content_and_can_decrypt(portal):
    result = portal.submit(
        project_id=7,
        student_name="Test Researcher",
        title="Temporary fixture",
        content="fixture-only payload",
        password="submission-password",
    )

    stored = portal.get_submission(result["id"])
    assert stored is not None
    assert stored["encrypted_content"] != "fixture-only payload"
    assert "fixture-only payload" not in stored["encrypted_content"]
    assert portal.decrypt_submission(result["id"], "submission-password") == "fixture-only payload"


def test_submission_filters_compose_without_overwriting_each_other(portal):
    portal.submit(1, "Alice", "A1", "one", "pw")
    portal.submit(1, "Bob", "B1", "two", "pw")
    portal.submit(2, "Alice", "A2", "three", "pw")
    portal.submit(1, "Alice", "A3", "four", "pw")
    alice_project_one = portal.get_submissions(project_id=1, student_name="Alice")

    assert len(alice_project_one) == 2
    assert {row["title"] for row in alice_project_one} == {"A1", "A3"}
    assert len(portal.get_submissions(project_id=2)) == 1
    assert len(portal.get_submissions(student_name="Bob")) == 1


def test_status_filter_and_combined_filters(portal):
    submitted = portal.submit(3, "Casey", "pending", "draft", "pw")
    reviewed = portal.submit(3, "Casey", "reviewed", "final", "pw")
    portal.review(reviewed["id"], "A", 92, "Reviewed fixture", "professor-password")

    pending = portal.get_submissions(project_id=3, student_name="Casey", status="submitted")
    graded = portal.get_submissions(project_id=3, student_name="Casey", status="reviewed")

    assert [row["id"] for row in pending] == [submitted["id"]]
    assert [row["id"] for row in graded] == [reviewed["id"]]


def test_review_feedback_is_encrypted_and_statistics_handle_empty_scores(portal):
    portal.submit(4, "Dana", "first", "one", "pw")
    second = portal.submit(4, "Dana", "second", "two", "pw")
    portal.review(second["id"], "B", 84, "Private feedback fixture", "professor-password")

    reviewed_row = portal.get_submission(second["id"])
    assert reviewed_row["professor_feedback"] != "Private feedback fixture"
    assert "Private feedback fixture" not in reviewed_row["professor_feedback"]
    assert audit_portal.decrypt_text(
        reviewed_row["professor_feedback"], "professor-password"
    ) == "Private feedback fixture"

    stats = portal.get_student_stats(4, "Dana")
    assert stats == {
        "student_name": "Dana",
        "project_id": 4,
        "total_submissions": 2,
        "reviewed": 1,
        "pending": 1,
        "returned": 0,
        "average_score": 84.0,
    }
    assert portal.get_student_stats(99, "Nobody")["average_score"] is None
