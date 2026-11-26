"""Unit tests for the dependency-free service API-key guard."""
import hmac

import pytest

from modules.service_api_auth import (
    APIKeyNotConfiguredError,
    InvalidAPIKeyError,
    verify_service_api_key,
)


@pytest.mark.parametrize("expected_key", [None, "", "   "])
def test_service_api_key_guard_fails_closed_when_server_key_is_unconfigured(expected_key):
    with pytest.raises(APIKeyNotConfiguredError):
        verify_service_api_key(expected_key, "provided-client-key")


@pytest.mark.parametrize("provided_key", [None, "", "   "])
def test_service_api_key_guard_rejects_missing_client_key(provided_key):
    with pytest.raises(InvalidAPIKeyError):
        verify_service_api_key("configured-server-key", provided_key)


def test_service_api_key_guard_rejects_wrong_client_key():
    with pytest.raises(InvalidAPIKeyError):
        verify_service_api_key("configured-server-key", "wrong-client-key")


def test_service_api_key_guard_rejects_unsupported_non_ascii_string_without_type_error():
    with pytest.raises(InvalidAPIKeyError):
        verify_service_api_key("configured-server-key", "ключ")


def test_service_api_key_guard_uses_constant_time_compare_and_accepts_exact_match(monkeypatch):
    calls = []
    real_compare_digest = hmac.compare_digest

    def observed_compare_digest(provided, expected):
        calls.append((provided, expected))
        return real_compare_digest(provided, expected)

    monkeypatch.setattr("modules.service_api_auth.hmac.compare_digest", observed_compare_digest)

    assert verify_service_api_key("configured-server-key", "configured-server-key") is True
    assert calls == [("configured-server-key", "configured-server-key")]
