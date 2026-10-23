from __future__ import annotations

import pytest

from scripts import platform_ledger_staging_smoke as smoke


def set_smoke_env(monkeypatch, *, url="https://staging.example.test", confirmation=smoke.CONFIRMATION):
    monkeypatch.setenv("PLATFORM_LEDGER_SMOKE_BASE_URL", url)
    monkeypatch.setenv("PLATFORM_LEDGER_SMOKE_API_KEY", "test-key-not-a-real-secret")
    monkeypatch.setenv("PLATFORM_LEDGER_SMOKE_CONFIRM", confirmation)


def test_smoke_refuses_known_production_host_before_network(monkeypatch, capsys):
    set_smoke_env(monkeypatch, url="https://notion-live-analyzer-api.onrender.com")

    def no_network(*args, **kwargs):
        raise AssertionError("production host guard must run before any network call")

    monkeypatch.setattr(smoke.requests, "Session", no_network)
    with pytest.raises(SystemExit):
        smoke.main()
    assert "known production API host" in capsys.readouterr().err


def test_smoke_requires_explicit_nonproduction_confirmation(monkeypatch, capsys):
    set_smoke_env(monkeypatch, confirmation="")

    def no_network(*args, **kwargs):
        raise AssertionError("confirmation guard must run before any network call")

    monkeypatch.setattr(smoke.requests, "Session", no_network)
    with pytest.raises(SystemExit):
        smoke.main()
    assert "confirmation is required" in capsys.readouterr().err


@pytest.mark.parametrize("url", [
    "http://staging.example.test",
    "https://user:password@staging.example.test",
    "https://staging.example.test/path",
    "https://staging.example.test?token=unsafe",
])
def test_smoke_rejects_unsafe_base_url_before_network(monkeypatch, capsys, url):
    set_smoke_env(monkeypatch, url=url)

    def no_network(*args, **kwargs):
        raise AssertionError("URL guard must run before any network call")

    monkeypatch.setattr(smoke.requests, "Session", no_network)
    with pytest.raises(SystemExit):
        smoke.main()
    assert "FAIL:" in capsys.readouterr().err


def valid_metrics():
    return {
        "total": 1, "queued": 0, "running": 0, "succeeded": 1,
        "failed": 0, "needs_review": 0, "expired_leases": 0,
        "oldest_queued_age_seconds": 0, "created_last_24h": 1,
        "finished_last_24h": 1, "sampled_at": "2026-10-23T12:00:00+00:00",
    }


def test_smoke_metrics_validator_accepts_aggregate_schema():
    assert smoke.validate_metrics(valid_metrics())["succeeded"] == 1


@pytest.mark.parametrize("change", [
    {"payload": {"sensitive": True}},
    {"total": 99},
    {"running": -1},
    {"queued": True},
    {"expired_leases": 1},
    {"sampled_at": ""},
    {"extra_field": "unexpected"},
])
def test_smoke_metrics_validator_rejects_inconsistent_or_sensitive_schema(change):
    payload = valid_metrics()
    payload.update(change)
    with pytest.raises(ValueError):
        smoke.validate_metrics(payload)



def test_smoke_metrics_transition_requires_this_job_to_be_counted():
    before = valid_metrics()
    after = valid_metrics()
    before.update({"total": 10, "succeeded": 5, "finished_last_24h": 4})
    after.update({"total": 11, "succeeded": 6, "finished_last_24h": 5})
    smoke.validate_successful_job_transition(before, after)


@pytest.mark.parametrize("field", ["succeeded", "finished_last_24h"])
def test_smoke_metrics_transition_rejects_stale_aggregate_counts(field):
    before = valid_metrics()
    after = valid_metrics()
    before.update({"total": 10, "succeeded": 5, "finished_last_24h": 4})
    after.update({"total": 11, "succeeded": 6, "finished_last_24h": 5})
    after[field] = before[field]
    with pytest.raises(ValueError):
        smoke.validate_successful_job_transition(before, after)
