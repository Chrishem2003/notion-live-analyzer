"""Unit tests for modules.security_config."""
import pytest

from modules import security_config


class TestPasswordHashing:
    def test_hash_and_verify_roundtrip(self):
        h = security_config.hash_password("s3cret!pass")
        assert security_config.verify_password("s3cret!pass", h) is True

    def test_wrong_password_rejected(self):
        h = security_config.hash_password("right-password")
        assert security_config.verify_password("wrong-password", h) is False

    def test_hashes_are_unique_salts(self):
        h1 = security_config.hash_password("same-password")
        h2 = security_config.hash_password("same-password")
        assert h1 != h2
        assert h1.startswith("scrypt$")

    def test_verify_empty_or_malformed(self):
        assert security_config.verify_password("x", "") is False
        assert security_config.verify_password("x", "not-a-valid-format") is False
        assert security_config.verify_password("x", "scrypt$2$1$1$zz$zz") is False


class TestSecretResolution:
    def test_env_var_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("MY_TEST_KEY", "from-env")
        assert security_config.get_env("MY_TEST_KEY", "default") == "from-env"

    def test_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("SOME_UNSET_VAR", raising=False)
        assert security_config.get_env("SOME_UNSET_VAR", "fallback") == "fallback"

    def test_empty_env_falls_through_to_default(self, monkeypatch):
        monkeypatch.setenv("EMPTY_VAR", "")
        assert security_config.get_env("EMPTY_VAR", "d") == "d"

    def test_dotenv_parser(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# comment\n"
            "SIMPLE=value\n"
            "QUOTED=\"hello world\"\n"
            "SINGLE='a b'\n"
            "EMPTY=\n"
        )
        parsed = security_config._dotenv_values(str(env_file))
        assert parsed["SIMPLE"] == "value"
        assert parsed["QUOTED"] == "hello world"
        assert parsed["SINGLE"] == "a b"
        assert "EMPTY" not in parsed or parsed["EMPTY"] == ""


class TestAdminSeeding:
    def test_is_admin_email_matches_seeded(self, monkeypatch):
        monkeypatch.setenv(security_config.SEED_ADMIN_EMAIL_ENV, "Owner@Example.com")
        assert security_config.is_admin_email("owner@example.com") is True

    def test_is_admin_email_rejects_other(self, monkeypatch):
        monkeypatch.setenv(security_config.SEED_ADMIN_EMAIL_ENV, "owner@example.com")
        assert security_config.is_admin_email("someone@example.com") is False
        assert security_config.is_admin_email("") is False

    def test_is_admin_email_additional_csv(self, monkeypatch):
        monkeypatch.setenv(security_config.SEED_ADMIN_EMAIL_ENV, "")
        monkeypatch.setenv("ADMIN_EMAILS", "a@x.com, B@y.com")
        assert security_config.is_admin_email("b@y.com") is True
        assert security_config.is_admin_email("c@z.com") is False

    def test_seed_admin_if_needed_creates_when_missing(self, monkeypatch):
        created = {}

        def get_user(email):
            return None

        def create_user(email, password_hash, role):
            created["email"] = email
            created["hash"] = password_hash
            created["role"] = role
            return {"email": email}

        monkeypatch.setenv(security_config.SEED_ADMIN_EMAIL_ENV, "admin@example.com")
        monkeypatch.setenv(security_config.SEED_ADMIN_PASSWORD_ENV, "admin-pass-123")

        result = security_config.seed_admin_if_needed(get_user, create_user)
        assert result == {"email": "admin@example.com"}
        assert created["role"] == "admin"
        # The stored password must be hashed, never the plaintext.
        assert created["hash"] != "admin-pass-123"
        assert created["hash"].startswith("scrypt$")

    def test_seed_admin_if_needed_skips_when_not_configured(self, monkeypatch):
        monkeypatch.delenv(security_config.SEED_ADMIN_EMAIL_ENV, raising=False)
        monkeypatch.delenv(security_config.SEED_ADMIN_PASSWORD_ENV, raising=False)
        assert security_config.seed_admin_if_needed(lambda e: None, lambda *a, **k: None) is None

    def test_seed_admin_if_needed_reuses_existing(self, monkeypatch):
        existing = {"email": "admin@example.com"}
        monkeypatch.setenv(security_config.SEED_ADMIN_EMAIL_ENV, "admin@example.com")
        monkeypatch.setenv(security_config.SEED_ADMIN_PASSWORD_ENV, "admin-pass-123")

        result = security_config.seed_admin_if_needed(
            lambda e: existing, lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not create"))
        )
        assert result is existing
