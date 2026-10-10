from __future__ import annotations

from dataclasses import dataclass

from sovereign_intelligence.models import AIRequest
from sovereign_intelligence.providers.circuit import (
    CircuitBreakerConfig,
    ProviderCircuitBreaker,
)
from sovereign_intelligence.providers.retry import (
    ProviderRetryPolicy,
    RetryPolicyConfig,
)
from sovereign_intelligence.providers.routing_models import (
    ProviderCandidate,
)
from sovereign_intelligence.providers.failover import (
    ProviderFailover,
)


@dataclass
class FakeResponse:
    provider: str
    model: str
    content: str


class FlakyProvider:
    def __init__(
        self,
        failures: int,
        name: str = "fake",
    ):
        self.failures = failures
        self.name = name
        self.calls = []

    def generate(self, request):
        self.calls.append(request)

        if len(self.calls) <= self.failures:
            raise TimeoutError(
                "request timed out"
            )

        return FakeResponse(
            provider=request.provider,
            model=request.model,
            content="success",
        )


class PermanentFailureProvider:
    def __init__(self):
        self.calls = []

    def generate(self, request):
        self.calls.append(request)

        raise RuntimeError(
            "401 Unauthorized: invalid API key"
        )


class AlwaysFailProvider:
    def __init__(self):
        self.calls = []

    def generate(self, request):
        self.calls.append(request)

        raise TimeoutError(
            "request timed out"
        )


def candidate(
    name: str,
    model: str,
    priority: int,
) -> ProviderCandidate:
    return ProviderCandidate(
        name=name,
        model=model,
        priority=priority,
        capabilities={"text"},
    )


def request() -> AIRequest:
    return AIRequest(prompt="hello", provider="original", model="original-model")


def test_retryable_failure_retries_same_provider():
    provider = FlakyProvider(
        failures=2,
        name="primary",
    )

    failover = ProviderFailover(
        providers={"primary": provider},
        candidates=[
            candidate(
                "primary",
                "primary-model",
                1,
            )
        ],
        retry_policy=ProviderRetryPolicy(
            RetryPolicyConfig(
                max_attempts=3,
                base_delay_seconds=10.0,
                jitter_ratio=0.0,
            )
        ),
        sleep_fn=lambda _: None,
    )

    result = failover.execute(
        request()
    )

    assert result.attempts[-1].success is True
    assert len(provider.calls) == 3


def test_retry_uses_same_provider_and_model():
    provider = FlakyProvider(
        failures=1,
        name="primary",
    )

    failover = ProviderFailover(
        providers={"primary": provider},
        candidates=[
            candidate(
                "primary",
                "primary-model",
                1,
            )
        ],
        retry_policy=ProviderRetryPolicy(
            RetryPolicyConfig(
                max_attempts=2,
                jitter_ratio=0.0,
            )
        ),
        sleep_fn=lambda _: None,
    )

    failover.execute(
        request()
    )

    assert all(
        call.provider == "primary"
        for call in provider.calls
    )

    assert all(
        call.model == "primary-model"
        for call in provider.calls
    )


def test_retry_does_not_mutate_original_request():
    provider = FlakyProvider(
        failures=1,
        name="primary",
    )

    original = request()

    failover = ProviderFailover(
        providers={"primary": provider},
        candidates=[
            candidate(
                "primary",
                "primary-model",
                1,
            )
        ],
        retry_policy=ProviderRetryPolicy(
            RetryPolicyConfig(
                max_attempts=2,
                jitter_ratio=0.0,
            )
        ),
        sleep_fn=lambda _: None,
    )

    failover.execute(
        original
    )

    assert original.provider == "original"
    assert original.model == "original-model"


def test_non_retryable_error_moves_to_fallback_immediately():
    primary = PermanentFailureProvider()
    fallback = FlakyProvider(
        failures=0,
        name="fallback",
    )

    failover = ProviderFailover(
        providers={
            "primary": primary,
            "fallback": fallback,
        },
        candidates=[
            candidate(
                "primary",
                "primary-model",
                1,
            ),
            candidate(
                "fallback",
                "fallback-model",
                2,
            ),
        ],
        retry_policy=ProviderRetryPolicy(
            RetryPolicyConfig(
                max_attempts=3,
                jitter_ratio=0.0,
            )
        ),
        sleep_fn=lambda _: None,
    )

    result = failover.execute(
        request()
    )

    assert len(primary.calls) == 1
    assert len(fallback.calls) == 1
    assert result.attempts[-1].success is True


def test_retry_limit_moves_to_fallback():
    primary = AlwaysFailProvider()
    fallback = FlakyProvider(
        failures=0,
        name="fallback",
    )

    failover = ProviderFailover(
        providers={
            "primary": primary,
            "fallback": fallback,
        },
        candidates=[
            candidate(
                "primary",
                "primary-model",
                1,
            ),
            candidate(
                "fallback",
                "fallback-model",
                2,
            ),
        ],
        retry_policy=ProviderRetryPolicy(
            RetryPolicyConfig(
                max_attempts=3,
                jitter_ratio=0.0,
            )
        ),
        sleep_fn=lambda _: None,
    )

    result = failover.execute(
        request()
    )

    assert len(primary.calls) == 3
    assert len(fallback.calls) == 1
    assert result.attempts[-1].success is True


def test_retry_records_error_category():
    provider = FlakyProvider(
        failures=1,
        name="primary",
    )

    failover = ProviderFailover(
        providers={"primary": provider},
        candidates=[
            candidate(
                "primary",
                "primary-model",
                1,
            )
        ],
        retry_policy=ProviderRetryPolicy(
            RetryPolicyConfig(
                max_attempts=2,
                jitter_ratio=0.0,
            )
        ),
        sleep_fn=lambda _: None,
    )

    result = failover.execute(
        request()
    )

    assert result.attempts[0].success is False
    assert result.attempts[0].error.startswith(
        "timeout:"
    )


def test_circuit_still_blocks_retry_after_threshold():
    primary = AlwaysFailProvider()
    fallback = FlakyProvider(
        failures=0,
        name="fallback",
    )

    circuit = ProviderCircuitBreaker(
        config=CircuitBreakerConfig(
            failure_threshold=2,
            cooldown_seconds=30.0,
        )
    )

    failover = ProviderFailover(
        providers={
            "primary": primary,
            "fallback": fallback,
        },
        candidates=[
            candidate(
                "primary",
                "primary-model",
                1,
            ),
            candidate(
                "fallback",
                "fallback-model",
                2,
            ),
        ],
        circuit_breaker=circuit,
        retry_policy=ProviderRetryPolicy(
            RetryPolicyConfig(
                max_attempts=5,
                jitter_ratio=0.0,
            )
        ),
        sleep_fn=lambda _: None,
    )

    result = failover.execute(
        request()
    )

    assert len(primary.calls) == 2
    assert len(fallback.calls) == 1

    assert any(
        attempt.error
        == "Provider circuit is open."
        for attempt in result.attempts
    )


def test_successful_retry_closes_circuit():
    provider = FlakyProvider(
        failures=1,
        name="primary",
    )

    circuit = ProviderCircuitBreaker(
        config=CircuitBreakerConfig(
            failure_threshold=3,
            cooldown_seconds=30.0,
        )
    )

    failover = ProviderFailover(
        providers={"primary": provider},
        candidates=[
            candidate(
                "primary",
                "primary-model",
                1,
            )
        ],
        circuit_breaker=circuit,
        retry_policy=ProviderRetryPolicy(
            RetryPolicyConfig(
                max_attempts=3,
                jitter_ratio=0.0,
            )
        ),
        sleep_fn=lambda _: None,
    )

    failover.execute(
        request()
    )

    health = circuit.health.get(
        "primary"
    )

    assert health.consecutive_failures == 0
    assert health.successes == 1
    assert health.circuit_state.value == "closed"
