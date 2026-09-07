import pytest

from sovereign_intelligence.providers.circuit import (
    CircuitBreakerConfig,
    ProviderCircuitBreaker,
)
from sovereign_intelligence.providers.health import (
    ProviderHealthRegistry,
)


def test_recovery_success_threshold_must_be_positive():
    with pytest.raises(
        ValueError,
        match="recovery_success_threshold must be greater than zero",
    ):
        ProviderCircuitBreaker(
            health_registry=ProviderHealthRegistry(),
            config=CircuitBreakerConfig(
                recovery_success_threshold=0,
            ),
        )


def test_negative_recovery_success_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="recovery_success_threshold must be greater than zero",
    ):
        ProviderCircuitBreaker(
            health_registry=ProviderHealthRegistry(),
            config=CircuitBreakerConfig(
                recovery_success_threshold=-1,
            ),
        )


def test_default_recovery_success_threshold_preserves_existing_behavior():
    config = CircuitBreakerConfig()

    assert config.recovery_success_threshold == 1
