from sovereign_intelligence.providers.circuit import (
    CircuitBreakerConfig,
    ProviderCircuitBreaker,
)
from sovereign_intelligence.providers.health import (
    CircuitState,
    ProviderHealthRegistry,
)


def test_recovery_success_threshold_requires_multiple_probes():
    registry = ProviderHealthRegistry()

    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=1,
            cooldown_seconds=0,
            recovery_success_threshold=2,
        ),
    )

    breaker.record_failure("openai")

    # First recovery probe.
    assert breaker.allow_request("openai") is True
    breaker.record_success("openai")

    # One successful recovery probe is not enough.
    assert registry.get("openai").circuit_state == CircuitState.HALF_OPEN


def test_recovery_success_threshold_closes_after_required_probes():
    registry = ProviderHealthRegistry()

    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=1,
            cooldown_seconds=0,
            recovery_success_threshold=2,
        ),
    )

    breaker.record_failure("openai")

    # Recovery probe 1.
    assert breaker.allow_request("openai") is True
    breaker.record_success("openai")

    # Recovery probe 2.
    assert breaker.allow_request("openai") is True
    breaker.record_success("openai")

    assert registry.get("openai").circuit_state == CircuitState.CLOSED


def test_recovery_failure_resets_success_progress():
    registry = ProviderHealthRegistry()

    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=1,
            cooldown_seconds=0,
            recovery_success_threshold=3,
        ),
    )

    breaker.record_failure("openai")

    # First recovery probe succeeds.
    assert breaker.allow_request("openai") is True
    breaker.record_success("openai")

    assert registry.get("openai").circuit_state == CircuitState.HALF_OPEN

    # Next recovery probe fails.
    assert breaker.allow_request("openai") is True
    breaker.record_failure("openai")

    assert registry.get("openai").circuit_state == CircuitState.OPEN
