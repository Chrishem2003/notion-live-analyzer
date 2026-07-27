"""Unit tests for modules.audit_portal."""
import pytest

from modules import audit_portal, professor_vault

PASSWORD = "cohort-2026!"


@pytest.fixture(autouse=True)
def fast_kdf(monkeypatch):
    """Production stretches 600k rounds; tests would otherwise crawl."""
    monkeypatch.setattr(professor_vault, "KDF_ROUNDS", 1_000)


@pytest.fixture
def system(tmp_path):
    portal = audit_portal.CHRISHEMSubmissionSystem(tmp_path / "portal.db")
    portal.set_vault_password(1, PASSWORD)
    return portal


class TestEncryption:
    def test_roundtrip(self):
        cipher = audit_portal.encrypt_text("secret work", PASSWORD)
        assert cipher != "secret work"
        assert audit_portal.decrypt_text(cipher, PASSWORD) == "secret work"

    def test_wrong_password_raises_rather_than_returning_a_string(self):
        """A failure string could be stored or shown as if it were the work."""
        cipher = audit_portal.encrypt_text("secret work", PASSWORD)
        with pytest.raises(professor_vault.VaultLocked):
            audit_portal.decrypt_text(cipher, "other-password")


class TestVaultPassword:
    def test_password_is_not_set_by_default(self, tmp_path):
        portal = audit_portal.CHRISHEMSubmissionSystem(tmp_path / "portal.db")
        assert not portal.vault_password_set(7)
        assert not portal.unlock(7, PASSWORD)

    def test_unlock_accepts_the_project_password(self, system):
        assert system.unlock(1, PASSWORD)

    def test_unlock_rejects_others(self, system):
        assert not system.unlock(1, "guess-the-password")

    def test_raw_password_is_never_stored(self, system, tmp_path):
        blob = (tmp_path / "portal.db").read_bytes()
        assert PASSWORD.encode() not in blob

    def test_weak_passwords_are_refused(self, system):
        with pytest.raises(professor_vault.VaultError):
            system.set_vault_password(2, "pw")

    def test_passwords_are_per_project(self, system):
        system.set_vault_password(2, "second-project-1")
        assert system.unlock(2, "second-project-1")
        assert not system.unlock(2, PASSWORD)

    def test_master_password_opens_any_project(self, system, monkeypatch):
        monkeypatch.setenv("FORENSIC_MASTER_PASSWORD", "deployment-recovery-1")
        assert system.unlock(1, "deployment-recovery-1")

    def test_no_master_password_means_no_backdoor(self, system, monkeypatch):
        monkeypatch.delenv("FORENSIC_MASTER_PASSWORD", raising=False)
        assert not system.unlock(1, "")


class TestSubmissions:
    def test_submit_returns_blockchain_hash(self, system):
        result = system.submit(1, "ada", "Thesis", "body text", PASSWORD)
        assert result["id"] == 1
        assert len(result["blockchain_hash"]) == 64

    def test_stored_content_is_encrypted(self, system, tmp_path):
        system.submit(1, "ada", "Thesis", "confidential body", PASSWORD)
        assert b"confidential body" not in (tmp_path / "portal.db").read_bytes()

    def test_decrypt_submission(self, system):
        result = system.submit(1, "ada", "Thesis", "body text", PASSWORD)
        assert system.decrypt_submission(result["id"], PASSWORD) == "body text"

    def test_decrypt_with_the_wrong_password_raises(self, system):
        result = system.submit(1, "ada", "Thesis", "body text", PASSWORD)
        with pytest.raises(professor_vault.VaultLocked):
            system.decrypt_submission(result["id"], "not-the-password")

    def test_decrypt_unknown_submission_is_none(self, system):
        assert system.decrypt_submission(999, PASSWORD) is None

    def test_filters(self, system):
        system.set_vault_password(2, "second-project-1")
        system.submit(1, "ada", "A", "x", PASSWORD)
        system.submit(2, "bob", "B", "y", "second-project-1")
        assert len(system.get_submissions()) == 2
        assert len(system.get_submissions(project_id=1)) == 1
        assert len(system.get_submissions(student_name="bob")) == 1
        assert len(system.get_submissions(status="reviewed")) == 0


class TestStudentStats:
    def test_stats_for_unknown_student(self, system):
        stats = system.get_student_stats(1, "nobody")
        assert stats["total_submissions"] == 0
        assert stats["average_score"] is None

    def test_stats_count_each_status(self, system):
        reviewed = system.submit(1, "ada", "A", "x", PASSWORD)["id"]
        returned = system.submit(1, "ada", "B", "y", PASSWORD)["id"]
        system.submit(1, "ada", "C", "z", PASSWORD)  # stays 'submitted'
        system.review(reviewed, "A", 90.0, "great", PASSWORD)
        system.return_for_revision(returned, "redo section 2", PASSWORD)

        stats = system.get_student_stats(1, "ada")
        assert stats["total_submissions"] == 3
        assert stats["reviewed"] == 1
        assert stats["pending"] == 1
        assert stats["returned"] == 1
        assert stats["average_score"] == 90.0

    def test_average_score_ignores_ungraded(self, system):
        first = system.submit(1, "ada", "A", "x", PASSWORD)["id"]
        second = system.submit(1, "ada", "B", "y", PASSWORD)["id"]
        system.submit(1, "ada", "C", "z", PASSWORD)
        system.review(first, "A", 80.0, "ok", PASSWORD)
        system.review(second, "B", 90.0, "ok", PASSWORD)
        assert system.get_student_stats(1, "ada")["average_score"] == 85.0


class TestFeedback:
    def test_feedback_is_encrypted_and_readable(self, system):
        submission_id = system.submit(1, "ada", "A", "x", PASSWORD)["id"]
        system.review(submission_id, "B+", 75.0, "tighten the argument", PASSWORD)
        record = system.get_submission(submission_id)
        assert "tighten the argument" not in str(record)
        assert (
            audit_portal.decrypt_text(record["professor_feedback"], PASSWORD)
            == "tighten the argument"
        )
