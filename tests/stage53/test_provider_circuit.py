from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from sovereign_intelligence.providers.circuit import (
    CircuitBreakerConfig,
    ProviderCircuitBreaker,
)
from sovereign_intelligence.providers.health import (
    CircuitState,
    ProviderHealthRegistry,
)


def test_single_failure_keeps_provider_available() -> None:
    registry = ProviderHealthRegistry()
    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=3,
            cooldown_seconds=30,
        ),
    )

    breaker.record_failure("openai")

    assert breaker.state("openai") == CircuitState.CLOSED
    assert breaker.allow_request("openai") is True


def test_failure_threshold_opens_circuit() -> None:
    registry = ProviderHealthRegistry()
    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=3,
            cooldown_seconds=30,
        ),
    )

    breaker.record_failure("openai")
    breaker.record_failure("openai")
    breaker.record_failure("openai")

    assert breaker.state("openai") == CircuitState.OPEN


def test_open_circuit_rejects_request() -> None:
    registry = ProviderHealthRegistry()
    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=2,
            cooldown_seconds=30,
        ),
    )

    breaker.record_failure("openai")
    breaker.record_failure("openai")

    assert breaker.state("openai") == CircuitState.OPEN
    assert breaker.allow_request("openai") is False


def test_cooldown_moves_open_circuit_to_half_open() -> None:
    registry = ProviderHealthRegistry()
    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=2,
            cooldown_seconds=30,
        ),
    )

    breaker.record_failure("openai")
    breaker.record_failure("openai")

    health = registry.get("openai")
    health.last_failure_at = (
        datetime.now(timezone.utc) - timedelta(seconds=31)
    ).isoformat()

    assert breaker.state("openai") == CircuitState.HALF_OPEN
    assert breaker.allow_request("openai") is True


def test_success_recovers_half_open_circuit_to_closed() -> None:
    registry = ProviderHealthRegistry()
    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=2,
            cooldown_seconds=30,
        ),
    )

    breaker.record_failure("openai")
    breaker.record_failure("openai")

    health = registry.get("openai")
    health.last_failure_at = (
        datetime.now(timezone.utc) - timedelta(seconds=31)
    ).isoformat()

    assert breaker.state("openai") == CircuitState.HALF_OPEN

    breaker.record_success("openai", latency_ms=12.5)

    assert breaker.state("openai") == CircuitState.CLOSED
    assert breaker.allow_request("openai") is True


def test_failed_half_open_recovery_reopens_circuit() -> None:
    registry = ProviderHealthRegistry()
    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=2,
            cooldown_seconds=30,
        ),
    )

    breaker.record_failure("openai")
    breaker.record_failure("openai")

    health = registry.get("openai")
    health.last_failure_at = (
        datetime.now(timezone.utc) - timedelta(seconds=31)
    ).isoformat()

    assert breaker.state("openai") == CircuitState.HALF_OPEN

    breaker.record_failure("openai")

    assert breaker.state("openai") == CircuitState.OPEN
    assert breaker.allow_request("openai") is False


def test_success_resets_consecutive_failure_count() -> None:
    registry = ProviderHealthRegistry()
    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=3,
            cooldown_seconds=30,
        ),
    )

    breaker.record_failure("openai")
    breaker.record_failure("openai")

    breaker.record_success("openai")

    health = registry.get("openai")

    assert health.consecutive_failures == 0
    assert health.circuit_state == CircuitState.CLOSED


def test_invalid_failure_threshold_is_rejected() -> None:
    with pytest.raises(ValueError):
        ProviderCircuitBreaker(
            config=CircuitBreakerConfig(
                failure_threshold=0,
                cooldown_seconds=30,
            )
        )


def test_negative_cooldown_is_rejected() -> None:
    with pytest.raises(ValueError):
        ProviderCircuitBreaker(
            config=CircuitBreakerConfig(
                failure_threshold=3,
                cooldown_seconds=-1,
            )
        )

from datetime import datetime, timedelta, timezone

from sovereign_intelligence.providers.circuit import (
    CircuitBreakerConfig,
    ProviderCircuitBreaker,
)
from sovereign_intelligence.providers.health import (
    CircuitState,
    ProviderHealthRegistry,
)


def test_half_open_allows_only_one_recovery_probe() -> None:
    registry = ProviderHealthRegistry()

    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=2,
            cooldown_seconds=30,
        ),
    )

    breaker.record_failure("openai")
    breaker.record_failure("openai")

    health = registry.get("openai")

    health.last_failure_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=31)
    ).isoformat()

    assert breaker.state("openai") == CircuitState.HALF_OPEN

    first_probe = breaker.allow_request("openai")
    second_probe = breaker.allow_request("openai")

    assert first_probe is True
    assert second_probe is False

    assert breaker.state("openai") == CircuitState.HALF_OPEN

    breaker.record_success(
        "openai",
        latency_ms=10.0,
    )

    assert breaker.state("openai") == CircuitState.CLOSED
    assert breaker.allow_request("openai") is True


def test_failed_half_open_probe_releases_probe_lock() -> None:
    registry = ProviderHealthRegistry()

    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=2,
            cooldown_seconds=30,
        ),
    )

    breaker.record_failure("openai")
    breaker.record_failure("openai")

    health = registry.get("openai")

    health.last_failure_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=31)
    ).isoformat()

    assert breaker.state("openai") == CircuitState.HALF_OPEN

    assert breaker.allow_request("openai") is True

    assert breaker.allow_request("openai") is False

    breaker.record_failure(
        "openai",
        latency_ms=25.0,
    )

    assert breaker.state("openai") == CircuitState.OPEN
    assert breaker.allow_request("openai") is False

    health.last_failure_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=31)
    ).isoformat()

    assert breaker.state("openai") == CircuitState.HALF_OPEN

    # The previous failed probe released its probe lock.
    assert breaker.allow_request("openai") is True
