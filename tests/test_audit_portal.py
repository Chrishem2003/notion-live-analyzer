

"""Unit tests for modules.audit_portal."""
import pytest

from modules import audit_portal


@pytest.fixture
def system(tmp_path):
    return audit_portal.CHRISHEMSubmissionSystem(tmp_path / "portal.db")


class TestEncryption:
    def test_roundtrip(self):
        cipher = audit_portal.encrypt_text("secret work", "pw")
        assert cipher != "secret work"
        assert audit_portal.decrypt_text(cipher, "pw") == "secret work"

    def test_wrong_password_fails_gracefully(self):
        cipher = audit_portal.encrypt_text("secret work", "pw")
        assert "failed" in audit_portal.decrypt_text(cipher, "other").lower()


class TestSubmissions:
    def test_submit_returns_blockchain_hash(self, system):
        result = system.submit(1, "ada", "Thesis", "body text")
        assert result["id"] == 1
        assert len(result["blockchain_hash"]) == 64

    def test_decrypt_submission(self, system):
        result = system.submit(1, "ada", "Thesis", "body text")
        assert system.decrypt_submission(result["id"], "CHRISHEM") == "body text"

    def test_decrypt_unknown_submission_is_none(self, system):
        assert system.decrypt_submission(999, "CHRISHEM") is None

    def test_filters(self, system):
        system.submit(1, "ada", "A", "x")
        system.submit(2, "bob", "B", "y")
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
        reviewed = system.submit(1, "ada", "A", "x")["id"]
        returned = system.submit(1, "ada", "B", "y")["id"]
        system.submit(1, "ada", "C", "z")  # stays 'submitted'
        system.review(reviewed, "A", 90.0, "great")
        system.return_for_revision(returned, "redo section 2")

        stats = system.get_student_stats(1, "ada")
        assert stats["total_submissions"] == 3
        assert stats["reviewed"] == 1
        assert stats["pending"] == 1
        assert stats["returned"] == 1
        assert stats["average_score"] == 90.0

    def test_average_score_ignores_ungraded(self, system):
        first = system.submit(1, "ada", "A", "x")["id"]
        second = system.submit(1, "ada", "B", "y")["id"]
        system.submit(1, "ada", "C", "z")
        system.review(first, "A", 80.0, "ok")
        system.review(second, "B", 90.0, "ok")
        assert system.get_student_stats(1, "ada")["average_score"] == 85.0
