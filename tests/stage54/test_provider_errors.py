from __future__ import annotations

from sovereign_intelligence.providers.errors import (
    ProviderErrorCategory,
    ProviderErrorClassifier,
)


def test_rate_limit_is_retryable():
    result = ProviderErrorClassifier.classify(
        "429 Too Many Requests: rate limit exceeded"
    )

    assert result.category == ProviderErrorCategory.RATE_LIMIT
    assert result.retryable is True


def test_timeout_is_retryable():
    result = ProviderErrorClassifier.classify(
        TimeoutError("request timed out")
    )

    assert result.category == ProviderErrorCategory.TIMEOUT
    assert result.retryable is True


def test_connection_is_retryable():
    result = ProviderErrorClassifier.classify(
        ConnectionError("connection refused")
    )

    assert result.category == ProviderErrorCategory.CONNECTION
    assert result.retryable is True


def test_provider_unavailable_is_retryable():
    result = ProviderErrorClassifier.classify(
        "503 Service Unavailable"
    )

    assert result.category == ProviderErrorCategory.PROVIDER_UNAVAILABLE
    assert result.retryable is True


def test_server_error_is_retryable():
    result = ProviderErrorClassifier.classify(
        "500 Internal Server Error"
    )

    assert result.category == ProviderErrorCategory.SERVER_ERROR
    assert result.retryable is True


def test_authentication_is_not_retryable():
    result = ProviderErrorClassifier.classify(
        "401 Unauthorized: invalid API key"
    )

    assert result.category == ProviderErrorCategory.AUTHENTICATION
    assert result.retryable is False


def test_configuration_is_not_retryable():
    result = ProviderErrorClassifier.classify(
        "Provider is not configured"
    )

    assert result.category == ProviderErrorCategory.CONFIGURATION
    assert result.retryable is False


def test_invalid_request_is_not_retryable():
    result = ProviderErrorClassifier.classify(
        "400 Bad Request: invalid parameter"
    )

    assert result.category == ProviderErrorCategory.INVALID_REQUEST
    assert result.retryable is False


def test_unknown_error_is_not_retryable():
    result = ProviderErrorClassifier.classify(
        "something unexpected happened"
    )

    assert result.category == ProviderErrorCategory.UNKNOWN
    assert result.retryable is False


def test_empty_error_is_safe():
    result = ProviderErrorClassifier.classify("")

    assert result.category == ProviderErrorCategory.UNKNOWN
    assert result.retryable is False
    assert result.reason == "Unknown provider error."
