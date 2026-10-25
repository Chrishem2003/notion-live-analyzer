from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

import sovereign_intelligence.api.service_router as intelligence_api


def make_client() -> TestClient:
    app = FastAPI()
    app.include_router(intelligence_api.router)
    return TestClient(app)


def test_providers_requires_configured_key(monkeypatch):
    monkeypatch.delenv("PLATFORM_API_KEY", raising=False)
    response = make_client().get("/api/v1/intelligence/providers")
    assert response.status_code == 503


def test_providers_rejects_wrong_key(monkeypatch):
    monkeypatch.setenv("PLATFORM_API_KEY", "test-secret")
    response = make_client().get(
        "/api/v1/intelligence/providers",
        headers={"X-API-Key": "wrong"},
    )
    assert response.status_code == 401


def test_providers_never_returns_credentials(monkeypatch):
    monkeypatch.setenv("PLATFORM_API_KEY", "test-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-leak")
    class FakeProviders:
        def configured_names(self):
            return ["openai"]
    class FakeConfig:
        default_provider = "openai"
        fallback_provider = None
    class FakeBrain:
        providers = FakeProviders()
        config = FakeConfig()
    monkeypatch.setattr(intelligence_api, "_get_brain", lambda: FakeBrain())
    response = make_client().get(
        "/api/v1/intelligence/providers",
        headers={"X-API-Key": "test-secret"},
    )
    assert response.status_code == 200
    assert response.json()["providers"] == ["openai"]
    assert "must-not-leak" not in response.text


def test_solve_validates_prompt_before_execution(monkeypatch):
    monkeypatch.setenv("PLATFORM_API_KEY", "test-secret")
    response = make_client().post(
        "/api/v1/intelligence/solve",
        headers={"X-API-Key": "test-secret"},
        json={"prompt": "   "},
    )
    assert response.status_code == 422


def test_solve_calls_governed_brain(monkeypatch):
    monkeypatch.setenv("PLATFORM_API_KEY", "test-secret")
    class FakeBrain:
        def solve_governed(self, **kwargs):
            assert kwargs["prompt"] == "Explain wetland monitoring"
            assert kwargs["provider"] == "google"
            return type("Result", (), {
                "answer": "Use repeat satellite observations.",
                "provider": "google",
                "model": "test-model",
                "sources": [],
                "verification": None,
                "assessment": type("Assessment", (), {"accepted": True})(),
                "control": type("Control", (), {
                    "action": type("Action", (), {"value": "allow"})()
                })(),
            })()
    monkeypatch.setattr(intelligence_api, "_get_brain", lambda: FakeBrain())
    response = make_client().post(
        "/api/v1/intelligence/solve",
        headers={"X-API-Key": "test-secret"},
        json={
            "prompt": "Explain wetland monitoring",
            "provider": "google",
            "strategy": "direct",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["provider"] == "google"
