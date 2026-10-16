"""Regression tests for the hardened audit portal submission store."""

import sqlite3

import pytest

from modules import audit_portal


def seed_submissions(db_path):
    audit_portal.CHRISHEMSubmissionSystem(db_path=db_path)
    rows = [
        (1, "Alice", "A", "ciphertext-a", 100.0, "submitted", None),
        (1, "Alice", "B", "ciphertext-b", 101.0, "reviewed", 80.0),
        (1, "Alice", "C", "ciphertext-c", 102.0, "returned", 90.0),
        (2, "Bob", "D", "ciphertext-d", 103.0, "submitted", None),
    ]
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO portal_submissions
                (project_id, student_name, title, encrypted_content,
                 submitted_at, status, professor_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def test_get_submissions_applies_each_filter_and_combination(tmp_path):
    db_path = tmp_path / "audit_portal.db"
    seed_submissions(db_path)
    system = audit_portal.CHRISHEMSubmissionSystem(db_path=db_path)

    assert len(system.get_submissions(project_id=1)) == 3
    assert len(system.get_submissions(student_name="Alice")) == 3
    assert len(system.get_submissions(status="submitted")) == 2
    filtered = system.get_submissions(
        project_id=1, student_name="Alice", status="reviewed"
    )
    assert len(filtered) == 1
    assert filtered[0]["title"] == "B"


def test_student_stats_include_counts_and_mean_of_available_scores(tmp_path):
    db_path = tmp_path / "audit_portal.db"
    seed_submissions(db_path)
    system = audit_portal.CHRISHEMSubmissionSystem(db_path=db_path)

    stats = system.get_student_stats(project_id=1, student_name="Alice")

    assert stats["total_submissions"] == 3
    assert stats["reviewed"] == 1
    assert stats["pending"] == 1
    assert stats["returned"] == 1
    assert stats["average_score"] == 85.0


@pytest.mark.skipif(
    not audit_portal.HAS_CRYPTOGRAPHY,
    reason="cryptography is not installed in this environment",
)
def test_salted_encryption_round_trip_and_wrong_password():
    plaintext = "private submission content"
    encrypted = audit_portal.encrypt_text(plaintext, "correct-password")

    assert encrypted.startswith("v2:")
    assert audit_portal.decrypt_text(encrypted, "correct-password") == plaintext
    wrong_password_result = audit_portal.decrypt_text(encrypted, "wrong-password")
    assert wrong_password_result.startswith("[🔒 Decryption failed:")
    assert plaintext not in wrong_password_result


@pytest.mark.skipif(
    not audit_portal.HAS_CRYPTOGRAPHY,
    reason="cryptography is not installed in this environment",
)
def test_legacy_ciphertext_remains_decryptable():
    legacy_key = audit_portal.derive_fernet_key(
        "legacy-password", audit_portal.LEGACY_SALT
    )
    encrypted = audit_portal.Fernet(legacy_key).encrypt(b"legacy submission")
    assert audit_portal.decrypt_text(
        encrypted.decode(), "legacy-password"
    ) == "legacy submission"


def test_missing_cryptography_never_falls_back_to_plaintext(monkeypatch):
    monkeypatch.setattr(audit_portal, "HAS_CRYPTOGRAPHY", False)

    with pytest.raises(audit_portal.CryptographyUnavailable):
        audit_portal.encrypt_text("must stay secret", "password")

    result = audit_portal.decrypt_text("not-an-encrypted-token", "password")
    assert result.startswith("[🔒")
    assert "must stay secret" not in result
