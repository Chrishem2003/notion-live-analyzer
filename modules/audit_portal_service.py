"""Configuration and authentication helpers for the live audit portal.

Secrets are supplied by Streamlit secrets or environment variables. There are
no built-in credentials or production defaults.
"""
from __future__ import annotations

import hmac
import os
from collections.abc import Mapping
from typing import Any


class PortalConfigurationError(RuntimeError):
    """Raised when required portal secrets are missing or invalid."""


def load_portal_credentials(
    secrets: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> tuple[str, str]:
    """Return (encryption_password, professor_password) from configured secrets.

    Streamlit secrets take precedence over environment variables. Empty or
    whitespace-only values are rejected; supplied passwords are not modified.
    """
    secret_values = secrets or {}
    environment = os.environ if environ is None else environ

    def configured_value(name: str) -> str | None:
        value = secret_values.get(name)
        if not isinstance(value, str) or not value.strip():
            value = environment.get(name)
        if not isinstance(value, str) or not value.strip():
            return None
        return value

    encryption_password = configured_value("AUDIT_PORTAL_ENCRYPTION_PASSWORD")
    professor_password = configured_value("AUDIT_PORTAL_PROFESSOR_PASSWORD")
    missing = []
    if encryption_password is None:
        missing.append("AUDIT_PORTAL_ENCRYPTION_PASSWORD")
    if professor_password is None:
        missing.append("AUDIT_PORTAL_PROFESSOR_PASSWORD")
    if missing:
        names = ", ".join(missing)
        raise PortalConfigurationError(
            f"Required audit-portal secret(s) are not configured: {names}."
        )
    return encryption_password, professor_password


def verify_professor_password(candidate: str, expected: str) -> bool:
    """Constant-time comparison for a configured professor access password."""
    if not isinstance(candidate, str) or not candidate:
        return False
    if not isinstance(expected, str) or not expected:
        return False
    return hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))
