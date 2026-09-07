from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from .health import CircuitState, ProviderHealthRegistry


@dataclass(frozen=True)
class CircuitBreakerConfig:
    failure_threshold: int = 3
    cooldown_seconds: float = 30.0
    recovery_success_threshold: int = 1


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

        if self.config.recovery_success_threshold <= 0:
            raise ValueError(
                "recovery_success_threshold must be greater "
                "than zero"
            )

        self._lock = Lock()
        self._half_open_probes: set[str] = set()
        self._recovery_successes: dict[str, int] = {}

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
                    self._recovery_successes[provider] = 0

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
                    self._recovery_successes[provider] = 0
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
            health = self.health.get(provider)

            self._half_open_probes.discard(provider)

            if health.circuit_state == CircuitState.HALF_OPEN:
                successes = (
                    self._recovery_successes.get(
                        provider,
                        0,
                    )
                    + 1
                )

                self._recovery_successes[provider] = (
                    successes
                )

                if (
                    successes
                    < self.config.recovery_success_threshold
                ):
                    health.total_attempts += 1
                    health.successes += 1
                    health.consecutive_failures = 0
                    health.total_latency_ms += max(
                        0.0,
                        float(latency_ms),
                    )
                    health.last_latency_ms = max(
                        0.0,
                        float(latency_ms),
                    )
                    health.last_success_at = (
                        datetime.now(timezone.utc).isoformat()
                    )
                    return

            self._recovery_successes.pop(provider, None)

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
            self._recovery_successes.pop(provider, None)

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
