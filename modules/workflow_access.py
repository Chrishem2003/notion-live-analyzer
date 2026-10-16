"""Explicit password gate for the local workflow execution console.

This is a single shared-secret operator gate, not an identity provider or role system.
Use a unique high-entropy secret in Streamlit secrets or the deployment environment.
"""
from __future__ import annotations

import hmac
import os
from typing import Mapping, Any

SESSION_TTL_SECONDS = 15 * 60
MIN_SECRET_LENGTH = 24


class WorkflowAccessConfigurationError(RuntimeError):
    """Raised when secure workflow access is not configured."""


def load_workflow_password(secrets: Mapping[str, Any] | None = None,
                           environ: Mapping[str, str] | None = None) -> str:
    """Read the operator secret without providing any insecure default."""
    secret_store = secrets or {}
    environment = environ or os.environ
    value = secret_store.get("WORKFLOW_EXECUTION_PASSWORD") or environment.get("WORKFLOW_EXECUTION_PASSWORD")
    if not isinstance(value, str) or len(value) < MIN_SECRET_LENGTH:
        raise WorkflowAccessConfigurationError(
            "WORKFLOW_EXECUTION_PASSWORD must be configured with at least 24 characters"
        )
    return value


def verify_workflow_password(candidate: str, expected: str) -> bool:
    """Constant-time compare for a submitted operator secret."""
    if not isinstance(candidate, str) or not isinstance(expected, str):
        return False
    return hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))


def is_workflow_session_valid(authenticated: bool, authenticated_at: Any,
                              *, now: float, ttl_seconds: int = SESSION_TTL_SECONDS) -> bool:
    """Validate an operator session timestamp; malformed/expired sessions fail closed."""
    if authenticated is not True or isinstance(authenticated_at, bool):
        return False
    if not isinstance(authenticated_at, (int, float)) or ttl_seconds < 1:
        return False
    age = now - float(authenticated_at)
    return 0 <= age < ttl_seconds
