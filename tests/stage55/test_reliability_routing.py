from sovereign_intelligence.providers.circuit import (
    CircuitBreakerConfig,
    ProviderCircuitBreaker,
)
from sovereign_intelligence.providers.health import ProviderHealthRegistry
from sovereign_intelligence.providers.router import ProviderRouter
from sovereign_intelligence.providers.routing_models import ProviderCandidate


def test_reliability_can_overcome_priority():
    health = ProviderHealthRegistry()

    for _ in range(9):
        health.record_failure("openai")

    for _ in range(9):
        health.record_success("openrouter", latency_ms=100.0)

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

    router = ProviderRouter(
        candidates,
        health_registry=health,
    )

    decision = router.route()

    assert decision.provider == "openrouter"


def test_lower_latency_influences_selection():
    health = ProviderHealthRegistry()

    for _ in range(10):
        health.record_success("openai", latency_ms=5000.0)

    for _ in range(10):
        health.record_success("openrouter", latency_ms=100.0)

    candidates = [
        ProviderCandidate(
            name="openai",
            model="gpt-5",
            priority=10,
        ),
        ProviderCandidate(
            name="openrouter",
            model="openrouter/auto",
            priority=10,
        ),
    ]

    router = ProviderRouter(
        candidates,
        health_registry=health,
    )

    decision = router.route()

    assert decision.provider == "openrouter"


def test_no_history_is_neutral():
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

    router = ProviderRouter(candidates)

    decision = router.route()

    assert decision.provider == "openai"


def test_capability_filtering_is_preserved():
    candidates = [
        ProviderCandidate(
            name="openai",
            model="gpt-5",
            priority=10,
            capabilities={"reasoning"},
        ),
        ProviderCandidate(
            name="openrouter",
            model="openrouter/auto",
            priority=20,
            capabilities={"coding"},
        ),
    ]

    router = ProviderRouter(candidates)

    decision = router.route(
        required_capabilities={"coding"},
    )

    assert decision.provider == "openrouter"


def test_preferred_provider_and_model_are_preserved():
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

    router = ProviderRouter(candidates)

    decision = router.route(
        preferred_provider="openrouter",
        preferred_model="custom-model",
    )

    assert decision.provider == "openrouter"
    assert decision.model == "custom-model"


def test_open_circuit_provider_is_excluded():
    breaker = ProviderCircuitBreaker(
        config=CircuitBreakerConfig(
            failure_threshold=2,
            cooldown_seconds=60.0,
        )
    )

    breaker.record_failure("openai")
    breaker.record_failure("openai")

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

    router = ProviderRouter(
        candidates,
        circuit_breaker=breaker,
    )

    decision = router.route()

    assert decision.provider == "openrouter"
