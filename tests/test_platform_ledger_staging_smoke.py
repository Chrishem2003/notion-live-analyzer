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
