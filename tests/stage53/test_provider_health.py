from __future__ import annotations

from sovereign_intelligence.providers.health import (
    CircuitState,
    ProviderHealth,
    ProviderHealthRegistry,
)


def test_provider_health_starts_clean():
    health = ProviderHealth(provider="openai")

    assert health.provider == "openai"
    assert health.total_attempts == 0
    assert health.successes == 0
    assert health.failures == 0
    assert health.consecutive_failures == 0
    assert health.success_rate == 0.0
    assert health.average_latency_ms == 0.0
    assert health.circuit_state == CircuitState.CLOSED


def test_success_updates_health_metrics():
    health = ProviderHealth(provider="openai")

    health.record_success(250.0)
    health.record_success(150.0)

    assert health.total_attempts == 2
    assert health.successes == 2
    assert health.failures == 0
    assert health.consecutive_failures == 0
    assert health.success_rate == 1.0
    assert health.average_latency_ms == 200.0
    assert health.last_latency_ms == 150.0
    assert health.last_success_at is not None
    assert health.circuit_state == CircuitState.CLOSED


def test_failure_updates_health_metrics():
    health = ProviderHealth(provider="openai")

    health.record_failure(100.0)
    health.record_failure(200.0)

    assert health.total_attempts == 2
    assert health.successes == 0
    assert health.failures == 2
    assert health.consecutive_failures == 2
    assert health.success_rate == 0.0
    assert health.last_latency_ms == 200.0
    assert health.last_failure_at is not None
    assert health.circuit_state == CircuitState.CLOSED


def test_success_resets_consecutive_failures():
    health = ProviderHealth(provider="openai")

    health.record_failure(100.0)
    health.record_failure(100.0)

    assert health.consecutive_failures == 2

    health.record_success(50.0)

    assert health.consecutive_failures == 0
    assert health.successes == 1
    assert health.failures == 2
    assert health.circuit_state == CircuitState.CLOSED


def test_registry_tracks_multiple_providers():
    registry = ProviderHealthRegistry()

    registry.record_failure("openai", 100.0)
    registry.record_failure("openai", 200.0)
    registry.record_success("openrouter", 300.0)

    snapshot = registry.snapshot()

    assert set(snapshot) == {"openai", "openrouter"}

    assert snapshot["openai"]["failures"] == 2
    assert snapshot["openai"]["consecutive_failures"] == 2

    assert snapshot["openrouter"]["successes"] == 1
    assert snapshot["openrouter"]["failures"] == 0
    assert snapshot["openrouter"]["success_rate"] == 1.0


def test_registry_get_is_stable():
    registry = ProviderHealthRegistry()

    first = registry.get("google")
    second = registry.get("google")

    assert first is second
    assert first.provider == "google"


def test_registry_reset_provider():
    registry = ProviderHealthRegistry()

    registry.record_failure("openai")

    assert "openai" in registry.snapshot()

    registry.reset("openai")

    assert "openai" not in registry.snapshot()


def test_registry_reset_all():
    registry = ProviderHealthRegistry()

    registry.record_failure("openai")
    registry.record_success("google")

    registry.reset()

    assert registry.snapshot() == {}


def test_snapshot_is_serializable():
    registry = ProviderHealthRegistry()

    registry.record_success("openrouter", 125.5)

    snapshot = registry.snapshot()

    assert snapshot["openrouter"]["provider"] == "openrouter"
    assert snapshot["openrouter"]["circuit_state"] == "closed"
    assert snapshot["openrouter"]["average_latency_ms"] == 125.5