"""Fail-closed service-to-service API key verification.

Keep this small and dependency-free so the authentication contract can be
tested without importing the full FastAPI application and its integrations.
"""
from __future__ import annotations

import hmac
from typing import Optional


class APIKeyNotConfiguredError(RuntimeError):
    """The server has no service API key configured."""


class InvalidAPIKeyError(RuntimeError):
    """The supplied service API key is missing or does not match."""


def verify_service_api_key(expected_key: Optional[str], provided_key: Optional[str]) -> bool:
    """Verify an exact API-key match using a constant-time comparison."""
    if not isinstance(expected_key, str) or not expected_key.strip():
        raise APIKeyNotConfiguredError("The server API key is not configured.")
    if not isinstance(provided_key, str) or not provided_key.strip():
        raise InvalidAPIKeyError("The API key is missing or invalid.")
    try:
        matches = hmac.compare_digest(provided_key, expected_key)
    except (TypeError, ValueError):
        # compare_digest only accepts supported string/byte inputs. Treat an
        # invalid encoding/type as an authentication failure, never a 500.
        matches = False
    if not matches:
        raise InvalidAPIKeyError("The API key is missing or invalid.")
    return True
