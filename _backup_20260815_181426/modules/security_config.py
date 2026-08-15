"""
security_config.py  centralized secret resolution, admin seeding, and password
hashing for the Notion Live Analyzer platform.

Security goals (UPGRADE_BRIEF.md, Section 0):
- Never hardcode credentials, API keys, or tokens in source code.
- Never commit real secrets. Read them from environment variables or a
  git-ignored ``.env`` / ``.streamlit/secrets.toml`` file at runtime only.
- The owner/admin account is seeded from environment variables at first-run
  setup, storing only a *hash* of the password, then the env vars are no
  longer needed.

This module is intentionally dependency-light: password hashing uses the
stdlib ``hashlib.scrypt`` (memory-hard, resistant to GPU/ASIC brute force).
For large production deployments you may swap this for bcrypt or argon2 by
implementing ``hash_password``/``verify_password`` with that library and
keeping the same call signatures here.
"""

from __future__ import annotations

import hashlib
import os
import hmac
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# .env loading (tiny, dependency-free) — only reads a local git-ignored file.
# ---------------------------------------------------------------------------

def _dotenv_values(path: str | Path) -> dict:
    """Parse a simple ``KEY=VALUE`` .env file into a dict.

    Lines starting with ``#`` are comments. Values may be quoted with single
    or double quotes. This is intentionally minimal — no external dependency.
    """
    values: dict = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip()
                if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                    val = val[1:-1]
                if key:
                    values[key] = val
    except OSError:
        # File missing or unreadable — fall through to env vars only.
        pass
    return values


# Cache the parsed .env so we don't re-read the file on every call.
_ENV_CACHE: Optional[dict] = None


def _load_dotenv_once() -> dict:
    global _ENV_CACHE
    if _ENV_CACHE is None:
        repo_root = Path(__file__).resolve().parent.parent
        _ENV_CACHE = _dotenv_values(repo_root / ".env")
    return _ENV_CACHE


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Resolve ``name`` from the process environment first, then a local .env.

    Resolution order matches the app's ``config.get_secret``:
    environment variable > local ``.env`` file > default.
    """
    value = os.environ.get(name)
    if value is not None and value != "":
        return value
    value = _load_dotenv_once().get(name)
    if value is not None and value != "":
        return value
    return default


# ---------------------------------------------------------------------------
# Admin seeding
# ---------------------------------------------------------------------------

SEED_ADMIN_EMAIL_ENV = "SEED_ADMIN_EMAIL"
SEED_ADMIN_PASSWORD_ENV = "SEED_ADMIN_PASSWORD"


def get_seed_admin_email() -> Optional[str]:
    """Return the configured owner/admin email, or None if not set.

    IMPORTANT: real values must live only in a local, git-ignored ``.env``
    (or environment variables). Never commit them.
    """
    return get_env(SEED_ADMIN_EMAIL_ENV)


def get_seed_admin_password() -> Optional[str]:
    """Return the configured owner/admin initial password, or None if unset.

    The caller must use this *only* at first-run setup to create a hashed
    record, then discard it. Do not store/log it.
    """
    return get_env(SEED_ADMIN_PASSWORD_ENV)


def is_admin_email(email: str) -> bool:
    """Server-side admin check driven purely by configuration.

    Preferred over the previous hardcoded ``chrishem242@gmail.com`` check.
    The admin list may additionally be supplied via ``ADMIN_EMAILS`` (a
    comma-separated env var) for multi-admin deployments.
    """
    if not email:
        return False
    email = email.strip().lower()

    # Primary: the seeded owner email.
    seeded = get_seed_admin_email()
    if seeded and seeded.strip().lower() == email:
        return True

    # Optional: csv list of additional admin emails.
    additional = get_env("ADMIN_EMAILS", "")
    for raw in additional.split(","):
        if raw.strip().lower() == email:
            return True
    return False


# ---------------------------------------------------------------------------
# Password hashing (stdlib scrypt — memory-hard PBKDF)
# ---------------------------------------------------------------------------

# scrypt parameters. Increase N for production/stronger hashing.
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16
_HASH_BYTES = 32


def hash_password(plaintext: str) -> str:
    """Hash a plaintext password with scrypt and return a self-describing string.

    Format: ``scrypt$<N>$<r>$<p>$<salt_hex>$<hash_hex>``
    """
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.scrypt(
        plaintext.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_HASH_BYTES,
    )
    return (
        f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}"
        f"${salt.hex()}${digest.hex()}"
    )


def verify_password(plaintext: str, stored_hash: str) -> bool:
    """Verify a plaintext password against a hash produced by ``hash_password``.

    Uses constant-time comparison (``hmac.compare_digest``) to avoid timing
    side channels.
    """
    if not stored_hash:
        return False
    parts = stored_hash.split("$")
    if len(parts) != 6 or parts[0] != "scrypt":
        return False
    try:
        n = int(parts[1])
        r = int(parts[2])
        p = int(parts[3])
        salt = bytes.fromhex(parts[4])
        expected = bytes.fromhex(parts[5])
    except (ValueError, TypeError):
        return False

    try:
        digest = hashlib.scrypt(
            plaintext.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


# ---------------------------------------------------------------------------
# Convenience: seed admin once at first-run setup
# ---------------------------------------------------------------------------

def seed_admin_if_needed(get_user_by_email_fn, create_user_fn):
    """Create the owner/admin account once from environment variables.

    Args:
        get_user_by_email_fn: callable(email) -> existing user obj or None
        create_user_fn: callable(email, password_hash, role) -> user obj

    Returns:
        The existing or newly created admin user, or None if not configured.

    This is *not* a Streamlit-rendering function — wire it into your app's
    startup/database initialization path. The password is hashed and the
    env vars are only read here.
    """
    email = get_seed_admin_email()
    password = get_seed_admin_password()
    if not email or not password:
        return None  # not configured — skip silently

    existing = get_user_by_email_fn(email)
    if existing:
        return existing

    return create_user_fn(
        email=email,
        password_hash=hash_password(password),
        role="admin",
    )
