"""Security regression tests for audit-portal encryption."""
from __future__ import annotations

import base64
import inspect

import pytest

import modules.audit_portal as portal


@pytest.mark.skipif(not portal.HAS_CRYPTOGRAPHY, reason="cryptography package unavailable")
def test_v2_round_trip_uses_random_per_record_salts():
    first = portal.encrypt_text("sensitive research", "a strong test password")
    second = portal.encrypt_text("sensitive research", "a strong test password")

    assert first.startswith("v2:")
    assert second.startswith("v2:")
    assert first != second
    assert portal.decrypt_text(first, "a strong test password") == "sensitive research"
    assert portal.decrypt_text(second, "a strong test password") == "sensitive research"


@pytest.mark.skipif(not portal.HAS_CRYPTOGRAPHY, reason="cryptography package unavailable")
def test_legacy_fernet_records_remain_readable():
    salt = portal.LEGACY_SALT
    token = portal.Fernet(portal.derive_fernet_key("legacy password", salt)).encrypt(
        b"legacy record"
    ).decode()

    assert portal.decrypt_text(token, "legacy password") == "legacy record"


@pytest.mark.skipif(not portal.HAS_CRYPTOGRAPHY, reason="cryptography package unavailable")
def test_wrong_password_returns_generic_error_without_crypto_details():
    token = portal.encrypt_text("secret", "correct password")

    with pytest.raises(ValueError, match="incorrect password or invalid ciphertext"):
        portal.decrypt_text(token, "wrong password")


@pytest.mark.skipif(not portal.HAS_CRYPTOGRAPHY, reason="cryptography package unavailable")
@pytest.mark.parametrize("password", ["", "   ", None])
def test_encryption_rejects_missing_or_blank_password(password):
    with pytest.raises(ValueError, match="non-empty password"):
        portal.encrypt_text("secret", password)


def test_missing_crypto_dependency_fails_closed(monkeypatch):
    monkeypatch.setattr(portal, "HAS_CRYPTOGRAPHY", False)

    with pytest.raises(portal.CryptographyUnavailable):
        portal.encrypt_text("secret", "password")


def test_submission_and_review_methods_have_no_default_passwords():
    assert inspect.signature(portal.CHRISHEMSubmissionSystem.submit).parameters["password"].default is inspect.Parameter.empty
    assert inspect.signature(portal.CHRISHEMSubmissionSystem.review).parameters["professor_password"].default is inspect.Parameter.empty
    assert inspect.signature(portal.CHRISHEMSubmissionSystem.return_for_revision).parameters["professor_password"].default is inspect.Parameter.empty

@pytest.mark.skipif(not portal.HAS_CRYPTOGRAPHY, reason="cryptography package unavailable")
@pytest.mark.parametrize("ciphertext", ["", "not-a-token", "v2:bad:not-a-token", "v2:YWJj:broken"])
def test_malformed_ciphertext_fails_with_generic_error(ciphertext):
    with pytest.raises(ValueError, match="Ciphertext must be a non-empty string|incorrect password or invalid ciphertext"):
        portal.decrypt_text(ciphertext, "password")


def test_root_compatibility_module_uses_canonical_hardened_implementation():
    import audit_portal as legacy

    assert legacy.CHRISHEMSubmissionSystem is portal.CHRISHEMSubmissionSystem
    encrypted = legacy.encrypt_text("compatibility", "test password")
    assert encrypted.startswith("v2:")
    assert legacy.decrypt_text(encrypted, "test password") == "compatibility"
