from __future__ import annotations

from .circuit import ProviderCircuitBreaker
from .health import CircuitState, ProviderHealthRegistry
from .routing_models import (
    ProviderCandidate,
    RoutingDecision,
)


class ProviderRouter:

    def __init__(
        self,
        candidates: list[ProviderCandidate],
        health_registry: ProviderHealthRegistry | None = None,
        circuit_breaker: ProviderCircuitBreaker | None = None,
    ):

        self.health = health_registry or (circuit_breaker.health if circuit_breaker is not None else ProviderHealthRegistry())
        self.circuit_breaker = circuit_breaker

        self.candidates = sorted(
            candidates,
            key=lambda item: item.priority,
        )

    def _score(self, candidate: ProviderCandidate, preferred_provider: str | None = None) -> tuple[int, float]:

        health = self.health.get(candidate.name)

        preferred_rank = 0 if (
            preferred_provider
            and candidate.name == preferred_provider
        ) else 1

        if health.total_attempts <= 1:
            reliability_penalty = 0.0
            latency_penalty = 0.0
        else:
            evidence_factor = min(
                (health.total_attempts - 1) / 2.0,
                1.0,
            )
            reliability_penalty = (
                (1.0 - health.success_rate)
                * 100.0
                * evidence_factor
            )
            latency_penalty = min(
                health.average_latency_ms / 1000.0,
                100.0,
            )

        return (
            preferred_rank,
            candidate.priority
            + reliability_penalty
            + latency_penalty,
        )

    def route(
        self,
        required_capabilities: set[str] | None = None,
        preferred_provider: str | None = None,
        preferred_model: str | None = None,
        exclude_open: bool = True,
    ) -> RoutingDecision:

        required = (
            required_capabilities
            or set()
        )

        candidates = [
            candidate
            for candidate in self.candidates
            if required.issubset(candidate.capabilities)
        ]

        if self.circuit_breaker is not None and exclude_open:
            candidates = [
                candidate
                for candidate in candidates
                if self.circuit_breaker.state(candidate.name).value != "open"
            ]

        if not candidates:
            raise RuntimeError(
                "No configured provider satisfies "
                "the requested capabilities."
            )

        candidates = sorted(
            candidates,
            key=lambda candidate: self._score(
                candidate,
                preferred_provider=preferred_provider,
            ),
        )

        selected = candidates[0]

        model = (
            preferred_model
            if (
                preferred_model
                and selected.name == preferred_provider
            )
            else selected.model
        )

        health = self.health.get(selected.name)

        if health.total_attempts <= 0:
            reason = (
                "Selected a provider satisfying the requested "
                "capabilities with no prior reliability history."
            )
        else:
            reason = (
                "Selected the provider using priority, historical "
                "success rate, and latency."
            )

        return RoutingDecision(
            provider=selected.name,
            model=model,
            reason=reason,
        )

        raise RuntimeError(
            "No configured provider satisfies "
            "the requested capabilities."
        )
