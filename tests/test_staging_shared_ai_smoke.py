from __future__ import annotations

import pytest

from scripts import staging_shared_ai_isolation_smoke as smoke


def test_staging_smoke_requires_https(monkeypatch):
    monkeypatch.setenv("STAGING_SHARED_AI_API_URL", "http://staging.example.test")
    with pytest.raises(SystemExit, match="HTTPS"):
        smoke.require_https_base()


def test_staging_smoke_refuses_production_render_host(monkeypatch):
    monkeypatch.setenv("STAGING_SHARED_AI_API_URL", "https://notion-live-analyzer.onrender.com")
    with pytest.raises(SystemExit, match="production Render hostname"):
        smoke.require_https_base()


def test_staging_smoke_accepts_named_staging_render_host(monkeypatch):
    monkeypatch.setenv("STAGING_SHARED_AI_API_URL", "https://notion-live-analyzer-staging.onrender.com/")
    assert smoke.require_https_base() == "https://notion-live-analyzer-staging.onrender.com"


def test_staging_smoke_request_adds_bearer_without_logging_token(monkeypatch):
    calls = []
    class FakeResponse:
        status_code = 200

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return FakeResponse()

    monkeypatch.setattr(smoke.requests, "request", fake_request)
    result = smoke.request("GET", "https://staging.example.test/api/v1/user-jobs", "secret-token")
    assert result.status_code == 200
    assert calls[0][2]["headers"]["Authorization"] == "Bearer secret-token"
