from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ProviderHealth:
    provider: str

    total_attempts: int = 0
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0

    total_latency_ms: float = 0.0
    last_latency_ms: float | None = None

    last_success_at: str | None = None
    last_failure_at: str | None = None

    circuit_state: CircuitState = CircuitState.CLOSED

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def average_latency_ms(self) -> float:
        if self.successes <= 0:
            return 0.0

        return self.total_latency_ms / self.successes

    @property
    def success_rate(self) -> float:
        if self.total_attempts <= 0:
            return 0.0

        return self.successes / self.total_attempts

    def record_success(self, latency_ms: float = 0.0) -> None:
        now = datetime.now(timezone.utc).isoformat()

        self.total_attempts += 1
        self.successes += 1
        self.consecutive_failures = 0

        self.total_latency_ms += max(
            0.0,
            float(latency_ms),
        )

        self.last_latency_ms = max(
            0.0,
            float(latency_ms),
        )

        self.last_success_at = now
        self.circuit_state = CircuitState.CLOSED

    def record_failure(self, latency_ms: float = 0.0) -> None:
        now = datetime.now(timezone.utc).isoformat()

        self.total_attempts += 1
        self.failures += 1
        self.consecutive_failures += 1

        self.last_latency_ms = max(
            0.0,
            float(latency_ms),
        )

        self.last_failure_at = now

    def snapshot(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "total_attempts": self.total_attempts,
            "successes": self.successes,
            "failures": self.failures,
            "consecutive_failures": self.consecutive_failures,
            "success_rate": self.success_rate,
            "average_latency_ms": self.average_latency_ms,
            "last_latency_ms": self.last_latency_ms,
            "last_success_at": self.last_success_at,
            "last_failure_at": self.last_failure_at,
            "circuit_state": self.circuit_state.value,
            "metadata": dict(self.metadata),
        }


class ProviderHealthRegistry:
    def __init__(self) -> None:
        self._health: dict[str, ProviderHealth] = {}
        self._lock = Lock()

    def get(self, provider: str) -> ProviderHealth:
        name = str(provider).strip()

        if not name:
            raise ValueError("provider must not be empty")

        with self._lock:
            health = self._health.get(name)

            if health is None:
                health = ProviderHealth(provider=name)
                self._health[name] = health

            return health

    def record_success(
        self,
        provider: str,
        latency_ms: float = 0.0,
    ) -> ProviderHealth:
        with self._lock:
            health = self._health.get(provider)

            if health is None:
                health = ProviderHealth(provider=provider)
                self._health[provider] = health

            health.record_success(latency_ms)
            return health

    def record_failure(
        self,
        provider: str,
        latency_ms: float = 0.0,
    ) -> ProviderHealth:
        with self._lock:
            health = self._health.get(provider)

            if health is None:
                health = ProviderHealth(provider=provider)
                self._health[provider] = health

            health.record_failure(latency_ms)
            return health

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {
                name: health.snapshot()
                for name, health in self._health.items()
            }

    def reset(self, provider: str | None = None) -> None:
        with self._lock:
            if provider is None:
                self._health.clear()
                return

            self._health.pop(provider, None)