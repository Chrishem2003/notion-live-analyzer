from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProviderErrorCategory(str, Enum):
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    AUTHENTICATION = "authentication"
    CONFIGURATION = "configuration"
    INVALID_REQUEST = "invalid_request"
    SERVER_ERROR = "server_error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProviderErrorClassification:
    category: ProviderErrorCategory
    retryable: bool
    reason: str


class ProviderErrorClassifier:
    """Classify provider failures into deterministic reliability categories."""

    _RATE_LIMIT_MARKERS = (
        "rate limit",
        "rate_limit",
        "too many requests",
        "429",
    )

    _TIMEOUT_MARKERS = (
        "timeout",
        "timed out",
        "deadline exceeded",
    )

    _CONNECTION_MARKERS = (
        "connection",
        "connection reset",
        "connection refused",
        "network",
        "dns",
        "name or service not known",
    )

    _UNAVAILABLE_MARKERS = (
        "service unavailable",
        "provider unavailable",
        "temporarily unavailable",
        "503",
        "502",
        "504",
    )

    _AUTH_MARKERS = (
        "authentication",
        "unauthorized",
        "invalid api key",
        "invalid_api_key",
        "api key",
        "401",
        "403",
    )

    _CONFIG_MARKERS = (
        "not configured",
        "configuration",
        "missing configuration",
        "missing api key",
    )

    _INVALID_REQUEST_MARKERS = (
        "invalid request",
        "invalid parameter",
        "bad request",
        "400",
    )

    _SERVER_MARKERS = (
        "internal server error",
        "server error",
        "500",
    )

    @classmethod
    def classify(
        cls,
        error: BaseException | str,
    ) -> ProviderErrorClassification:
        message = str(error).strip()
        normalized = message.lower()

        if isinstance(error, (TimeoutError,)):
            return ProviderErrorClassification(
                category=ProviderErrorCategory.TIMEOUT,
                retryable=True,
                reason="Provider request timed out.",
            )

        if isinstance(error, (ConnectionError,)):
            return ProviderErrorClassification(
                category=ProviderErrorCategory.CONNECTION,
                retryable=True,
                reason="Provider connection failed.",
            )

        category = cls._match_category(normalized)

        if category == ProviderErrorCategory.RATE_LIMIT:
            return ProviderErrorClassification(
                category=category,
                retryable=True,
                reason="Provider rate limit was reached.",
            )

        if category == ProviderErrorCategory.TIMEOUT:
            return ProviderErrorClassification(
                category=category,
                retryable=True,
                reason="Provider request timed out.",
            )

        if category == ProviderErrorCategory.CONNECTION:
            return ProviderErrorClassification(
                category=category,
                retryable=True,
                reason="Provider connection failed.",
            )

        if category == ProviderErrorCategory.PROVIDER_UNAVAILABLE:
            return ProviderErrorClassification(
                category=category,
                retryable=True,
                reason="Provider is temporarily unavailable.",
            )

        if category == ProviderErrorCategory.SERVER_ERROR:
            return ProviderErrorClassification(
                category=category,
                retryable=True,
                reason="Provider returned a server-side error.",
            )

        if category == ProviderErrorCategory.AUTHENTICATION:
            return ProviderErrorClassification(
                category=category,
                retryable=False,
                reason="Provider authentication failed.",
            )

        if category == ProviderErrorCategory.CONFIGURATION:
            return ProviderErrorClassification(
                category=category,
                retryable=False,
                reason="Provider configuration is invalid or missing.",
            )

        if category == ProviderErrorCategory.INVALID_REQUEST:
            return ProviderErrorClassification(
                category=category,
                retryable=False,
                reason="Provider rejected the request as invalid.",
            )

        return ProviderErrorClassification(
            category=ProviderErrorCategory.UNKNOWN,
            retryable=False,
            reason=message or "Unknown provider error.",
        )

    @classmethod
    def _match_category(
        cls,
        normalized: str,
    ) -> ProviderErrorCategory:
        if cls._contains_any(normalized, cls._RATE_LIMIT_MARKERS):
            return ProviderErrorCategory.RATE_LIMIT

        if cls._contains_any(normalized, cls._TIMEOUT_MARKERS):
            return ProviderErrorCategory.TIMEOUT

        if cls._contains_any(normalized, cls._CONNECTION_MARKERS):
            return ProviderErrorCategory.CONNECTION

        if cls._contains_any(normalized, cls._UNAVAILABLE_MARKERS):
            return ProviderErrorCategory.PROVIDER_UNAVAILABLE

        if cls._contains_any(normalized, cls._AUTH_MARKERS):
            return ProviderErrorCategory.AUTHENTICATION

        if cls._contains_any(normalized, cls._CONFIG_MARKERS):
            return ProviderErrorCategory.CONFIGURATION

        if cls._contains_any(normalized, cls._INVALID_REQUEST_MARKERS):
            return ProviderErrorCategory.INVALID_REQUEST

        if cls._contains_any(normalized, cls._SERVER_MARKERS):
            return ProviderErrorCategory.SERVER_ERROR

        return ProviderErrorCategory.UNKNOWN

    @staticmethod
    def _contains_any(
        message: str,
        markers: tuple[str, ...],
    ) -> bool:
        return any(marker in message for marker in markers)
