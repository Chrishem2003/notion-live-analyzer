from __future__ import annotations

from dataclasses import replace
from time import perf_counter, sleep
from typing import Callable

from .circuit import (
    CircuitBreakerConfig,
    ProviderCircuitBreaker,
)
from .retry import (
    ProviderRetryPolicy,
    RetryPolicyConfig,
)
from .routing_models import (
    ProviderAttempt,
    ProviderCandidate,
    RoutingResult,
)
from .router import ProviderRouter


class ProviderFailover:

    def __init__(
        self,
        providers: dict[str, object],
        candidates: list[ProviderCandidate],
        circuit_breaker: ProviderCircuitBreaker | None = None,
        retry_policy: ProviderRetryPolicy | None = None,
        retry_policy_config: RetryPolicyConfig | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ):

        self.providers = providers

        self.router = ProviderRouter(
            candidates
        )

        self.circuit_breaker = (
            circuit_breaker
            or ProviderCircuitBreaker(
                config=CircuitBreakerConfig()
            )
        )

        self.retry_policy = (
            retry_policy
            or ProviderRetryPolicy(
                config=retry_policy_config
            )
        )

        self._sleep = sleep_fn or sleep

    def execute(
        self,
        request,
        required_capabilities=None,
        preferred_provider=None,
        preferred_model=None,
    ):

        decision = self.router.route(
            required_capabilities=(
                required_capabilities
            ),
            preferred_provider=(
                preferred_provider
            ),
            preferred_model=(
                preferred_model
            ),
        )

        ordered = list(
            self.router.candidates
        )

        selected_index = next(
            (
                index
                for index, candidate
                in enumerate(ordered)
                if (
                    candidate.name
                    == decision.provider
                    and candidate.model
                    == decision.model
                )
            ),
            0,
        )

        ordered = ordered[
            selected_index:
        ]

        attempts = []

        for candidate in ordered:

            if not (
                (
                    required_capabilities
                    or set()
                ).issubset(
                    candidate.capabilities
                )
            ):
                continue

            provider = self.providers.get(
                candidate.name
            )

            if provider is None:

                attempts.append(
                    ProviderAttempt(
                        provider=candidate.name,
                        model=candidate.model,
                        success=False,
                        error=(
                            "Provider is not "
                            "configured."
                        ),
                    )
                )

                continue

            attempt_number = 1

            while True:

                if not self.circuit_breaker.allow_request(
                    candidate.name
                ):

                    attempts.append(
                        ProviderAttempt(
                            provider=candidate.name,
                            model=candidate.model,
                            success=False,
                            error=(
                                "Provider circuit "
                                "is open."
                            ),
                        )
                    )

                    break

                started = perf_counter()

                try:

                    attempt_request = replace(
                        request,
                        provider=candidate.name,
                        model=candidate.model,
                    )

                    response = provider.generate(
                        attempt_request
                    )

                    latency_ms = (
                        perf_counter() - started
                    ) * 1000.0

                    self.circuit_breaker.record_success(
                        candidate.name,
                        latency_ms=latency_ms,
                    )

                    attempts.append(
                        ProviderAttempt(
                            provider=candidate.name,
                            model=candidate.model,
                            success=True,
                            response=response,
                        )
                    )

                    return RoutingResult(
                        decision=decision,
                        attempts=attempts,
                    )

                except Exception as exc:

                    latency_ms = (
                        perf_counter() - started
                    ) * 1000.0

                    self.circuit_breaker.record_failure(
                        candidate.name,
                        latency_ms=latency_ms,
                    )

                    retry_decision = (
                        self.retry_policy.decide(
                            exc,
                            attempt=attempt_number,
                        )
                    )

                    attempts.append(
                        ProviderAttempt(
                            provider=candidate.name,
                            model=candidate.model,
                            success=False,
                            error=(
                                f"{retry_decision.category.value}: "
                                f"{exc}"
                            ),
                        )
                    )

                    if not retry_decision.retry:
                        break

                    self._sleep(
                        retry_decision.delay_seconds
                    )

                    attempt_number += 1

        raise RuntimeError(
            "All eligible AI providers failed."
        )
