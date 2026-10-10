from sovereign_intelligence.providers.circuit import (
    CircuitBreakerConfig,
    ProviderCircuitBreaker,
)
from sovereign_intelligence.providers.health import (
    CircuitState,
    ProviderHealthRegistry,
)


def test_open_circuit_transitions_to_half_open_after_cooldown():
    registry = ProviderHealthRegistry()

    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=1,
            cooldown_seconds=0,
        ),
    )

    breaker.record_failure("openai")

    # With zero cooldown, querying state immediately permits recovery.
    assert breaker.state("openai") == CircuitState.HALF_OPEN


def test_half_open_allows_only_one_probe():
    registry = ProviderHealthRegistry()

    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=1,
            cooldown_seconds=0,
        ),
    )

    breaker.record_failure("openai")

    assert breaker.allow_request("openai") is True
    assert breaker.allow_request("openai") is False


def test_successful_recovery_closes_circuit():
    registry = ProviderHealthRegistry()

    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=1,
            cooldown_seconds=0,
        ),
    )

    breaker.record_failure("openai")

    assert breaker.allow_request("openai") is True

    breaker.record_success("openai")

    assert breaker.state("openai") == CircuitState.CLOSED
    assert breaker.allow_request("openai") is True


def test_failed_recovery_reopens_circuit():
    registry = ProviderHealthRegistry()

    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=1,
            cooldown_seconds=0,
        ),
    )

    breaker.record_failure("openai")

    assert breaker.allow_request("openai") is True

    # The recovery probe fails.
    breaker.record_failure("openai")

    # Inspect the stored state before state() performs another
    # zero-cooldown recovery transition.
    assert registry.get("openai").circuit_state == CircuitState.OPEN


def test_failed_recovery_probe_does_not_leave_provider_stuck_half_open():
    registry = ProviderHealthRegistry()

    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=1,
            cooldown_seconds=0,
        ),
    )

    breaker.record_failure("openai")

    assert breaker.allow_request("openai") is True

    breaker.record_failure("openai")

    # Failed recovery must put the circuit back into OPEN internally.
    assert registry.get("openai").circuit_state == CircuitState.OPEN

    # Because cooldown is zero, a new recovery probe may subsequently
    # be permitted.
    assert breaker.allow_request("openai") is True
    assert breaker.allow_request("openai") is False
