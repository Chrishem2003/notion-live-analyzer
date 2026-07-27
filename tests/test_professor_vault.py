"""Unit tests for modules.professor_vault."""
import pytest

from modules import professor_vault as vault

# Real deployments stretch 600k rounds; tests would spend minutes on it.
FAST = 1_000


@pytest.fixture(autouse=True)
def fast_kdf(monkeypatch):
    monkeypatch.setattr(vault, "KDF_ROUNDS", FAST)


class TestEnvelope:
    def test_roundtrip(self):
        sealed = vault.encrypt("thesis chapter one", "correct horse 7")
        assert "thesis" not in sealed
        assert vault.decrypt(sealed, "correct horse 7") == "thesis chapter one"

    def test_unicode_survives(self):
        sealed = vault.encrypt("résumé — Ωmega 中文", "correct horse 7")
        assert vault.decrypt(sealed, "correct horse 7") == "résumé — Ωmega 中文"

    def test_empty_plaintext_is_allowed(self):
        sealed = vault.encrypt("", "correct horse 7")
        assert vault.decrypt(sealed, "correct horse 7") == ""

    def test_wrong_password_raises(self):
        sealed = vault.encrypt("secret", "correct horse 7")
        with pytest.raises(vault.VaultLocked):
            vault.decrypt(sealed, "wrong horse 7")

    def test_empty_password_is_refused(self):
        with pytest.raises(vault.VaultError):
            vault.encrypt("secret", "")

    def test_same_plaintext_gives_different_ciphertext(self):
        first = vault.encrypt("secret", "correct horse 7")
        second = vault.encrypt("secret", "correct horse 7")
        assert first != second, "per-record salt and nonce must randomise output"

    def test_salt_is_per_record(self):
        salts = {vault.encrypt("x", "correct horse 7").split("$")[2] for _ in range(5)}
        assert len(salts) == 5

    def test_envelope_declares_scheme_and_rounds(self):
        scheme, rounds, _, _, _ = vault.encrypt("x", "pw12345678").split("$")
        assert scheme == vault.SCHEME
        assert int(rounds) == FAST

    def test_is_sealed(self):
        assert vault.is_sealed(vault.encrypt("x", "pw12345678"))
        assert not vault.is_sealed("gAAAAABlegacy")
        assert not vault.is_sealed("")

    def test_tampered_ciphertext_is_rejected(self):
        sealed = vault.encrypt("secret", "correct horse 7")
        head, _, tail = sealed.rpartition("$")
        flipped = ("A" if tail[0] != "A" else "B") + tail[1:]
        with pytest.raises(vault.VaultLocked):
            vault.decrypt(f"{head}${flipped}", "correct horse 7")

    def test_tampered_header_is_rejected(self):
        """The header is associated data, so editing the rounds must fail."""
        scheme, rounds, salt, nonce, body = vault.encrypt("secret", "pw12345678").split("$")
        with pytest.raises(vault.VaultLocked):
            vault.decrypt(f"{scheme}${int(rounds) + 1}${salt}${nonce}${body}", "pw12345678")

    def test_garbage_payload_raises_locked_not_valueerror(self):
        with pytest.raises(vault.VaultLocked):
            vault.decrypt("not-an-envelope", "pw12345678")

    def test_unknown_scheme_is_rejected(self):
        _, rounds, salt, nonce, body = vault.encrypt("x", "pw12345678").split("$")
        with pytest.raises(vault.VaultLocked):
            vault.decrypt(f"pv9${rounds}${salt}${nonce}${body}", "pw12345678")


class TestLegacyFernet:
    def test_open_any_reads_a_legacy_record(self):
        import base64

        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"CHRISHEM_AUDIT_PORTAL_SALT_2024",
            iterations=600000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(b"oldpassword"))
        legacy = Fernet(key).encrypt(b"archived thesis").decode()

        assert vault.open_any(legacy, "oldpassword") == "archived thesis"

    def test_legacy_wrong_password_raises(self):
        with pytest.raises(vault.VaultLocked):
            vault.decrypt_legacy_fernet("gAAAAABnot-a-real-token", "oldpassword")

    def test_open_any_prefers_the_new_scheme(self):
        sealed = vault.encrypt("new record", "pw12345678")
        assert vault.open_any(sealed, "pw12345678") == "new record"


class TestPasswordPolicy:
    @pytest.mark.parametrize(
        "password",
        ["", "short1!", "password", "CHRISHEM", "12345678", "abcdefghij", "1234567890"],
    )
    def test_weak_passwords_are_rejected(self, password):
        assert not vault.check_password_strength(password).ok

    @pytest.mark.parametrize("password", ["marking-2026!", "Cohort7Vault", "a1b2c3d4e5"])
    def test_reasonable_passwords_pass(self, password):
        assert vault.check_password_strength(password).ok

    def test_rejection_explains_itself(self):
        assert "8" in vault.check_password_strength("ab1").reason


class TestVerifier:
    def test_verifier_matches_its_password(self):
        encoded = vault.password_verifier("marking-2026!", rounds=FAST)
        assert vault.verify("marking-2026!", encoded)

    def test_verifier_rejects_others(self):
        encoded = vault.password_verifier("marking-2026!", rounds=FAST)
        assert not vault.verify("marking-2027!", encoded)

    def test_verifier_never_stores_the_password(self):
        encoded = vault.password_verifier("marking-2026!", rounds=FAST)
        assert "marking-2026!" not in encoded

    def test_verifier_is_salted(self):
        first = vault.password_verifier("marking-2026!", rounds=FAST)
        second = vault.password_verifier("marking-2026!", rounds=FAST)
        assert first != second

    @pytest.mark.parametrize("bad", ["", "nonsense", "md5$1$a$b", None])
    def test_malformed_verifiers_are_false(self, bad):
        assert not vault.verify("marking-2026!", bad)


class TestMasterPassword:
    def test_absent_by_default(self, monkeypatch):
        monkeypatch.delenv("FORENSIC_MASTER_PASSWORD", raising=False)
        assert vault.master_password() is None

    def test_blank_counts_as_absent(self, monkeypatch):
        monkeypatch.setenv("FORENSIC_MASTER_PASSWORD", "")
        assert vault.master_password() is None

    def test_reads_the_environment(self, monkeypatch):
        monkeypatch.setenv("FORENSIC_MASTER_PASSWORD", "recovery-key-1")
        assert vault.master_password() == "recovery-key-1"


class TestBackendGuard:
    def test_missing_backend_refuses_rather_than_faking_it(self, monkeypatch):
        """No silent base64: a missing library must not look like encryption."""
        monkeypatch.setattr(vault, "HAS_CRYPTOGRAPHY", False)
        with pytest.raises(vault.VaultUnavailable):
            vault.encrypt("secret", "pw12345678")
        with pytest.raises(vault.VaultUnavailable):
            vault.decrypt("pv2$1$a$b$c", "pw12345678")
