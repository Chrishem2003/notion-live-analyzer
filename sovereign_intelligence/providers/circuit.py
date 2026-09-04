from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from .health import CircuitState, ProviderHealthRegistry


@dataclass(frozen=True)
class CircuitBreakerConfig:
    failure_threshold: int = 3
    cooldown_seconds: float = 30.0


class ProviderCircuitBreaker:
    def __init__(
        self,
        health_registry: ProviderHealthRegistry | None = None,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        self.health = health_registry or ProviderHealthRegistry()
        self.config = config or CircuitBreakerConfig()

        if self.config.failure_threshold <= 0:
            raise ValueError(
                "failure_threshold must be greater than zero"
            )

        if self.config.cooldown_seconds < 0:
            raise ValueError(
                "cooldown_seconds must not be negative"
            )

        self._lock = Lock()
        self._half_open_probes: set[str] = set()

    def state(self, provider: str) -> CircuitState:
        with self._lock:
            health = self.health.get(provider)

            if health.circuit_state == CircuitState.OPEN:
                if self._cooldown_elapsed(
                    health.last_failure_at
                ):
                    health.circuit_state = (
                        CircuitState.HALF_OPEN
                    )

            return health.circuit_state

    def allow_request(self, provider: str) -> bool:
        with self._lock:
            health = self.health.get(provider)

            if health.circuit_state == CircuitState.OPEN:
                if self._cooldown_elapsed(
                    health.last_failure_at
                ):
                    health.circuit_state = (
                        CircuitState.HALF_OPEN
                    )
                else:
                    return False

            if health.circuit_state == CircuitState.HALF_OPEN:
                if provider in self._half_open_probes:
                    return False

                self._half_open_probes.add(provider)

                return True

            return True

    def record_success(
        self,
        provider: str,
        latency_ms: float = 0.0,
    ) -> None:
        with self._lock:
            self._half_open_probes.discard(provider)

            self.health.record_success(
                provider,
                latency_ms,
            )

    def record_failure(
        self,
        provider: str,
        latency_ms: float = 0.0,
    ) -> None:
        with self._lock:
            self._half_open_probes.discard(provider)

            health = self.health.record_failure(
                provider,
                latency_ms,
            )

            if (
                health.consecutive_failures
                >= self.config.failure_threshold
            ):
                health.circuit_state = CircuitState.OPEN

    def _cooldown_elapsed(
        self,
        last_failure_at: str | None,
    ) -> bool:
        if not last_failure_at:
            return True

        try:
            failure_time = datetime.fromisoformat(
                last_failure_at
            )
        except ValueError:
            return True

        now = datetime.now(timezone.utc)

        elapsed = (
            now - failure_time
        ).total_seconds()

        return elapsed >= self.config.cooldown_seconds
