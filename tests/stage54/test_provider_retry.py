from __future__ import annotations

from random import Random

import pytest

from sovereign_intelligence.providers.errors import (
    ProviderErrorCategory,
)
from sovereign_intelligence.providers.retry import (
    ProviderRetryPolicy,
    RetryPolicyConfig,
)


def test_retryable_error_requests_retry():
    policy = ProviderRetryPolicy(
        RetryPolicyConfig(
            max_attempts=3,
            base_delay_seconds=1.0,
            jitter_ratio=0.0,
        )
    )

    result = policy.decide(
        TimeoutError("request timed out"),
        attempt=1,
    )

    assert result.retry is True
    assert result.category == ProviderErrorCategory.TIMEOUT
    assert result.delay_seconds == 1.0


def test_exponential_backoff_increases_delay():
    policy = ProviderRetryPolicy(
        RetryPolicyConfig(
            max_attempts=5,
            base_delay_seconds=1.0,
            jitter_ratio=0.0,
        )
    )

    first = policy.decide(
        "timeout",
        attempt=1,
    )
    second = policy.decide(
        "timeout",
        attempt=2,
    )
    third = policy.decide(
        "timeout",
        attempt=3,
    )

    assert first.delay_seconds == 1.0
    assert second.delay_seconds == 2.0
    assert third.delay_seconds == 4.0


def test_delay_is_capped():
    policy = ProviderRetryPolicy(
        RetryPolicyConfig(
            max_attempts=10,
            base_delay_seconds=2.0,
            max_delay_seconds=5.0,
            jitter_ratio=0.0,
        )
    )

    result = policy.decide(
        "timeout",
        attempt=5,
    )

    assert result.retry is True
    assert result.delay_seconds == 5.0


def test_jitter_is_bounded():
    policy = ProviderRetryPolicy(
        RetryPolicyConfig(
            max_attempts=5,
            base_delay_seconds=10.0,
            jitter_ratio=0.25,
        ),
        rng=Random(42),
    )

    result = policy.decide(
        "timeout",
        attempt=1,
    )

    assert 7.5 <= result.delay_seconds <= 12.5


def test_retry_stops_at_max_attempts():
    policy = ProviderRetryPolicy(
        RetryPolicyConfig(
            max_attempts=3,
            jitter_ratio=0.0,
        )
    )

    result = policy.decide(
        "timeout",
        attempt=3,
    )

    assert result.retry is False
    assert result.delay_seconds == 0.0


@pytest.mark.parametrize(
    "error",
    [
        "401 Unauthorized",
        "403 Forbidden",
        "Provider is not configured",
        "400 Bad Request",
    ],
)
def test_permanent_errors_are_not_retried(error):
    policy = ProviderRetryPolicy()

    result = policy.decide(
        error,
        attempt=1,
    )

    assert result.retry is False
    assert result.delay_seconds == 0.0


def test_rate_limit_is_retryable():
    policy = ProviderRetryPolicy(
        RetryPolicyConfig(
            jitter_ratio=0.0,
        )
    )

    result = policy.decide(
        "429 Too Many Requests",
        attempt=1,
    )

    assert result.retry is True
    assert result.category == ProviderErrorCategory.RATE_LIMIT


def test_invalid_attempt_is_rejected():
    policy = ProviderRetryPolicy()

    with pytest.raises(ValueError):
        policy.decide(
            "timeout",
            attempt=0,
        )


def test_invalid_configuration_is_rejected():
    with pytest.raises(ValueError):
        ProviderRetryPolicy(
            RetryPolicyConfig(
                max_attempts=0,
            )
        )

    with pytest.raises(ValueError):
        ProviderRetryPolicy(
            RetryPolicyConfig(
                base_delay_seconds=-1,
            )
        )

    with pytest.raises(ValueError):
        ProviderRetryPolicy(
            RetryPolicyConfig(
                jitter_ratio=-1,
            )
        )


def test_zero_delay_is_supported():
    policy = ProviderRetryPolicy(
        RetryPolicyConfig(
            base_delay_seconds=0.0,
            max_delay_seconds=0.0,
            jitter_ratio=0.0,
        )
    )

    result = policy.decide(
        "timeout",
        attempt=1,
    )

    assert result.retry is True
    assert result.delay_seconds == 0.0
