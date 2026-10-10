from sovereign_intelligence.providers.circuit import (
    CircuitBreakerConfig,
    ProviderCircuitBreaker,
)
from sovereign_intelligence.providers.failover import ProviderFailover
from sovereign_intelligence.providers.routing_models import ProviderCandidate


class FakeProvider:
    def generate(self, request):
        return "ok"


def test_failover_and_router_share_circuit_breaker():
    breaker = ProviderCircuitBreaker(
        config=CircuitBreakerConfig(
            failure_threshold=2,
            cooldown_seconds=60.0,
        )
    )

    candidates = [
        ProviderCandidate(
            name="openai",
            model="gpt-5",
            priority=10,
        ),
        ProviderCandidate(
            name="openrouter",
            model="openrouter/auto",
            priority=20,
        ),
    ]

    failover = ProviderFailover(
        providers={
            "openai": FakeProvider(),
            "openrouter": FakeProvider(),
        },
        candidates=candidates,
        circuit_breaker=breaker,
    )

    assert failover.router.circuit_breaker is failover.circuit_breaker
    assert failover.router.health is failover.circuit_breaker.health


def test_router_observes_failover_circuit_state():
    breaker = ProviderCircuitBreaker(
        config=CircuitBreakerConfig(
            failure_threshold=2,
            cooldown_seconds=60.0,
        )
    )

    candidates = [
        ProviderCandidate(
            name="openai",
            model="gpt-5",
            priority=10,
        ),
        ProviderCandidate(
            name="openrouter",
            model="openrouter/auto",
            priority=20,
        ),
    ]

    failover = ProviderFailover(
        providers={
            "openai": FakeProvider(),
            "openrouter": FakeProvider(),
        },
        candidates=candidates,
        circuit_breaker=breaker,
    )

    failover.circuit_breaker.record_failure("openai")
    failover.circuit_breaker.record_failure("openai")

    decision = failover.router.route()

    assert decision.provider == "openrouter"
