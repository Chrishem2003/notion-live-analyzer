from __future__ import annotations

import httpx
import pytest

from sovereign_intelligence.api.client import IntelligenceServiceClient, IntelligenceServiceError


def test_client_requires_safe_absolute_url_and_key():
    with pytest.raises(ValueError, match="absolute HTTP"):
        IntelligenceServiceClient("not-a-url", "secret")
    with pytest.raises(ValueError, match="required"):
        IntelligenceServiceClient("https://example.com", " ")


def test_client_sends_key_only_in_server_side_header(monkeypatch):
    seen = {}

    def fake_request(method, url, **kwargs):
        seen.update(method=method, url=url, **kwargs)
        return httpx.Response(200, json={"providers": ["ollama"], "default_provider": "ollama"})

    monkeypatch.setattr(httpx, "request", fake_request)
    client = IntelligenceServiceClient("https://api.example.com/", "test-secret")
    result = client.providers()

    assert result["providers"] == ["ollama"]
    assert seen["url"] == "https://api.example.com/api/v1/intelligence/providers"
    assert seen["headers"]["X-API-Key"] == "test-secret"
    assert "test-secret" not in seen["url"]


def test_solve_validates_prompt_and_checks_answer(monkeypatch):
    client = IntelligenceServiceClient("https://api.example.com", "test-secret")
    with pytest.raises(ValueError, match="non-empty"):
        client.solve("   ")

    def fake_request(method, url, **kwargs):
        assert kwargs["json"]["provider"] == "ollama"
        return httpx.Response(200, json={"answer": "A grounded answer", "status": "completed"})

    monkeypatch.setattr(httpx, "request", fake_request)
    result = client.solve("Help me", provider="ollama")
    assert result["answer"] == "A grounded answer"


def test_client_sanitizes_auth_error(monkeypatch):
    def fake_request(*args, **kwargs):
        return httpx.Response(401, json={"detail": "secret details"})

    monkeypatch.setattr(httpx, "request", fake_request)
    client = IntelligenceServiceClient("https://api.example.com", "test-secret")
    with pytest.raises(IntelligenceServiceError, match="credentials") as exc:
        client.providers()
    assert "secret details" not in str(exc.value)
    assert "test-secret" not in str(exc.value)
