"""
Professor Vault — authenticated encryption for student submissions
==================================================================
Envelope format (a single ASCII string, safe for a TEXT column)::

    pv2$<pbkdf2-rounds>$<b64 salt>$<b64 nonce>$<b64 ciphertext+tag>

AES-256-GCM with a per-record random salt and nonce. The header is fed to the
cipher as associated data, so tampering with the rounds or the salt fails the
tag check instead of silently decrypting to garbage.

Two deliberate differences from the older ``audit_portal`` helpers:

* A wrong password raises :class:`VaultLocked` rather than returning a string
  that looks like plaintext to every caller that does not inspect it.
* When ``cryptography`` is missing this module raises
  :class:`VaultUnavailable`. The previous base64 "fallback" stored submissions
  in plain sight while the UI claimed they were encrypted, which is worse than
  refusing to store them at all.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from typing import Optional

try:  # pragma: no cover - exercised by the import guard tests
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    HAS_CRYPTOGRAPHY = True
except ImportError:  # pragma: no cover
    HAS_CRYPTOGRAPHY = False
    AESGCM = None
    InvalidTag = Exception

SCHEME = "pv2"
KDF_ROUNDS = 600_000
SALT_BYTES = 16
NONCE_BYTES = 12
MIN_PASSWORD_LENGTH = 8


class VaultError(Exception):
    """Base class for vault failures."""


class VaultUnavailable(VaultError):
    """Raised when the encryption backend is not installed."""


class VaultLocked(VaultError):
    """Raised when a payload cannot be authenticated with the given password."""


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode()


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode())


def _require_backend() -> None:
    if not HAS_CRYPTOGRAPHY:
        raise VaultUnavailable(
            "The 'cryptography' package is required to open or seal the vault. "
            "Install it with: pip install 'cryptography>=41.0.0'"
        )


def derive_key(password: str, salt: bytes, rounds: Optional[int] = None) -> bytes:
    """Stretch a password into a 32-byte AES key."""
    if not password:
        raise VaultError("A vault password is required.")
    rounds = rounds or KDF_ROUNDS
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds, dklen=32)


def encrypt(plaintext: str, password: str, rounds: Optional[int] = None) -> str:
    """Seal ``plaintext`` into a self-describing envelope string."""
    _require_backend()
    if not password:
        raise VaultError("A vault password is required.")
    rounds = rounds or KDF_ROUNDS
    salt = secrets.token_bytes(SALT_BYTES)
    nonce = secrets.token_bytes(NONCE_BYTES)
    header = f"{SCHEME}${rounds}${_b64(salt)}${_b64(nonce)}"
    ciphertext = AESGCM(derive_key(password, salt, rounds)).encrypt(
        nonce, plaintext.encode(), header.encode()
    )
    return f"{header}${_b64(ciphertext)}"


def is_sealed(payload: str) -> bool:
    """True when ``payload`` looks like an envelope this module can open."""
    return isinstance(payload, str) and payload.startswith(f"{SCHEME}$")


def decrypt(payload: str, password: str) -> str:
    """Open an envelope. Raises :class:`VaultLocked` on a wrong password."""
    _require_backend()
    try:
        scheme, rounds, salt_b64, nonce_b64, ciphertext_b64 = payload.split("$")
        salt, nonce = _unb64(salt_b64), _unb64(nonce_b64)
        ciphertext = _unb64(ciphertext_b64)
        rounds_int = int(rounds)
    except (AttributeError, ValueError) as exc:
        raise VaultLocked(f"Unrecognised vault payload: {exc}") from exc
    if scheme != SCHEME:
        raise VaultLocked(f"Unsupported vault scheme '{scheme}'.")
    header = f"{scheme}${rounds}${salt_b64}${nonce_b64}"
    try:
        opened = AESGCM(derive_key(password, salt, rounds_int)).decrypt(
            nonce, ciphertext, header.encode()
        )
    except InvalidTag as exc:
        raise VaultLocked("Incorrect password, or the record was modified.") from exc
    return opened.decode()


def decrypt_legacy_fernet(payload: str, password: str) -> str:
    """Open a record written by the pre-``pv2`` Fernet helpers.

    Kept so existing submissions stay readable; nothing writes this format.
    """
    _require_backend()
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    legacy_salt = b"CHRISHEM_AUDIT_PORTAL_SALT_2024"
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=legacy_salt, iterations=600000
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    try:
        return Fernet(key).decrypt(payload.encode()).decode()
    except (InvalidToken, ValueError) as exc:
        raise VaultLocked("Incorrect password for this legacy record.") from exc


def open_any(payload: str, password: str) -> str:
    """Open either envelope format, newest first."""
    if is_sealed(payload):
        return decrypt(payload, password)
    return decrypt_legacy_fernet(payload, password)


# ═══════════════════════════════════════════════════════════════════════
# Password policy and verifiers
# ═══════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class PasswordCheck:
    ok: bool
    reason: str = ""


def check_password_strength(password: str) -> PasswordCheck:
    """Reject passwords that make the whole envelope pointless."""
    if not password:
        return PasswordCheck(False, "Choose a vault password.")
    if len(password) < MIN_PASSWORD_LENGTH:
        return PasswordCheck(
            False, f"Use at least {MIN_PASSWORD_LENGTH} characters."
        )
    if password.lower() in {"password", "chrishem", "12345678", "changeme"}:
        return PasswordCheck(False, "That password is too easy to guess.")
    if password.isdigit() or password.isalpha():
        return PasswordCheck(False, "Mix letters with digits or symbols.")
    return PasswordCheck(True)


def password_verifier(password: str, rounds: Optional[int] = None) -> str:
    """A storable hash used to tell a wrong password from an empty vault.

    Same construction as the account password hash; kept separate because the
    professor's vault password must never be the account password.
    """
    rounds = rounds or KDF_ROUNDS
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), rounds
    ).hex()
    return f"pbkdf2_sha256${rounds}${salt}${digest}"


def verify(password: str, verifier: str) -> bool:
    """Constant-time check against :func:`password_verifier` output."""
    try:
        algorithm, rounds, salt, digest = verifier.split("$")
    except (AttributeError, ValueError):
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), int(rounds)
    ).hex()
    return hmac.compare_digest(candidate, digest)


def master_password() -> Optional[str]:
    """Deployment-wide fallback password, or ``None`` when unset."""
    return os.environ.get("FORENSIC_MASTER_PASSWORD") or None
