from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from sovereign_intelligence.models import AIRequest
from sovereign_intelligence.providers.circuit import (
    CircuitBreakerConfig,
    ProviderCircuitBreaker,
)
from sovereign_intelligence.providers.failover import ProviderFailover
from sovereign_intelligence.providers.health import (
    CircuitState,
    ProviderHealthRegistry,
)
from sovereign_intelligence.providers.routing_models import (
    ProviderCandidate,
)


@dataclass
class FakeProvider:
    name: str
    failures_before_success: int = 0
    calls: list[AIRequest] = field(default_factory=list)

    def generate(self, request: AIRequest) -> dict[str, Any]:
        self.calls.append(request)

        if len(self.calls) <= self.failures_before_success:
            raise RuntimeError(
                f"{self.name} simulated failure"
            )

        return {
            "provider": self.name,
            "model": request.model,
            "answer": f"{self.name} success",
        }


def make_request() -> AIRequest:
    return AIRequest(
        prompt="Test circuit-aware failover",
        provider="openai",
        model="primary-model",
    )


def make_candidates() -> list[ProviderCandidate]:
    return [
        ProviderCandidate(
            name="openai",
            model="primary-model",
            priority=10,
        ),
        ProviderCandidate(
            name="openrouter",
            model="fallback-model",
            priority=20,
        ),
    ]


def make_failover(
    primary: FakeProvider,
    fallback: FakeProvider,
) -> tuple[
    ProviderFailover,
    ProviderCircuitBreaker,
]:
    registry = ProviderHealthRegistry()

    breaker = ProviderCircuitBreaker(
        health_registry=registry,
        config=CircuitBreakerConfig(
            failure_threshold=2,
            cooldown_seconds=300,
        ),
    )

    failover = ProviderFailover(
        providers={
            "openai": primary,
            "openrouter": fallback,
        },
        candidates=make_candidates(),
        circuit_breaker=breaker,
    )

    return failover, breaker


def test_primary_failure_opens_circuit_and_fallback_succeeds() -> None:
    primary = FakeProvider(
        name="openai",
        failures_before_success=100,
    )

    fallback = FakeProvider(
        name="openrouter",
        failures_before_success=0,
    )

    failover, breaker = make_failover(
        primary,
        fallback,
    )

    request = make_request()

    first_result = failover.execute(request)

    assert len(primary.calls) == 1
    assert len(fallback.calls) == 1
    assert first_result.attempts[0].provider == "openai"
    assert first_result.attempts[0].success is False
    assert first_result.attempts[1].provider == "openrouter"
    assert first_result.attempts[1].success is True

    second_result = failover.execute(request)

    assert len(primary.calls) == 2
    assert len(fallback.calls) == 2
    assert second_result.attempts[0].provider == "openai"
    assert second_result.attempts[0].success is False
    assert second_result.attempts[1].provider == "openrouter"
    assert second_result.attempts[1].success is True

    assert (
        breaker.state("openai")
        == CircuitState.OPEN
    )

    third_result = failover.execute(request)

    assert len(primary.calls) == 2
    assert len(fallback.calls) == 3

    assert third_result.attempts[0].provider == "openai"
    assert third_result.attempts[0].success is False
    assert (
        third_result.attempts[0].error
        == "Provider circuit is open."
    )

    assert third_result.attempts[1].provider == "openrouter"
    assert third_result.attempts[1].success is True


def test_fallback_receives_correct_provider_and_model() -> None:
    primary = FakeProvider(
        name="openai",
        failures_before_success=1,
    )

    fallback = FakeProvider(
        name="openrouter",
        failures_before_success=0,
    )

    failover, _ = make_failover(
        primary,
        fallback,
    )

    request = make_request()

    result = failover.execute(request)

    assert result.attempts[-1].success is True

    assert len(fallback.calls) == 1
    fallback_request = fallback.calls[0]

    assert fallback_request.provider == "openrouter"
    assert fallback_request.model == "fallback-model"


def test_original_request_is_not_mutated() -> None:
    primary = FakeProvider(
        name="openai",
        failures_before_success=1,
    )

    fallback = FakeProvider(
        name="openrouter",
        failures_before_success=0,
    )

    failover, _ = make_failover(
        primary,
        fallback,
    )

    request = make_request()

    original_provider = request.provider
    original_model = request.model

    failover.execute(request)

    assert request.provider == original_provider
    assert request.model == original_model


def test_successful_provider_does_not_open_circuit() -> None:
    primary = FakeProvider(
        name="openai",
        failures_before_success=0,
    )

    fallback = FakeProvider(
        name="openrouter",
        failures_before_success=0,
    )

    failover, breaker = make_failover(
        primary,
        fallback,
    )

    result = failover.execute(
        make_request()
    )

    assert result.attempts[-1].success is True
    assert len(primary.calls) == 1
    assert len(fallback.calls) == 0

    assert (
        breaker.state("openai")
        == CircuitState.CLOSED
    )


def test_open_primary_is_recorded_as_skipped_attempt() -> None:
    primary = FakeProvider(
        name="openai",
        failures_before_success=100,
    )

    fallback = FakeProvider(
        name="openrouter",
        failures_before_success=0,
    )

    failover, breaker = make_failover(
        primary,
        fallback,
    )

    breaker.record_failure("openai")
    breaker.record_failure("openai")

    assert (
        breaker.state("openai")
        == CircuitState.OPEN
    )

    result = failover.execute(
        make_request()
    )

    assert len(primary.calls) == 0
    assert len(fallback.calls) == 1

    assert (
        result.attempts[0].error
        == "Provider circuit is open."
    )
    assert result.attempts[1].provider == "openrouter"
    assert result.attempts[1].success is True
