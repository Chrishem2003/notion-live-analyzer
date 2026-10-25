"""Regression tests for bounded lifetimes on server-issued chat tokens."""
import base64
import json

from fastapi.testclient import TestClient

import api_server


def _payload(token: str) -> dict:
    encoded, _signature = token.rsplit(".", 1)
    return json.loads(base64.urlsafe_b64decode(encoded.encode("ascii")))


def test_chat_token_endpoint_supports_short_lifetime_for_shared_ai(monkeypatch):
    monkeypatch.setattr(api_server, "API_KEY", "test-platform-key")
    monkeypatch.setenv("CHAT_TOKEN_SECRET", "test-chat-token-secret")
    monkeypatch.setenv("SHARED_AI_LEGACY_EMAIL_TOKEN_ISSUER_ENABLED", "true")
    response = TestClient(api_server.app).post(
        "/api/v1/chat/token",
        params={"email": "Alice@example.com", "ttl_seconds": 300},
        headers={"X-API-Key": "test-platform-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["expires_in_seconds"] == 300
    payload = _payload(body["token"])
    assert payload["email"] == "alice@example.com"
    assert 240 <= payload["exp"] - __import__("time").time() <= 300


def test_chat_token_endpoint_rejects_unbounded_lifetimes(monkeypatch):
    monkeypatch.setattr(api_server, "API_KEY", "test-platform-key")
    monkeypatch.setenv("CHAT_TOKEN_SECRET", "test-chat-token-secret")
    monkeypatch.setenv("SHARED_AI_LEGACY_EMAIL_TOKEN_ISSUER_ENABLED", "true")
    client = TestClient(api_server.app)

    too_short = client.post(
        "/api/v1/chat/token",
        params={"email": "alice@example.com", "ttl_seconds": 10},
        headers={"X-API-Key": "test-platform-key"},
    )
    too_long = client.post(
        "/api/v1/chat/token",
        params={"email": "alice@example.com", "ttl_seconds": 86400},
        headers={"X-API-Key": "test-platform-key"},
    )

    assert too_short.status_code == 422
    assert too_long.status_code == 422



def test_chat_token_issuer_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(api_server, "API_KEY", "test-platform-key")
    monkeypatch.setenv("CHAT_TOKEN_SECRET", "test-chat-token-secret")
    monkeypatch.delenv("SHARED_AI_LEGACY_EMAIL_TOKEN_ISSUER_ENABLED", raising=False)

    response = TestClient(api_server.app).post(
        "/api/v1/chat/token",
        params={"email": "alice@example.com", "ttl_seconds": 300},
        headers={"X-API-Key": "test-platform-key"},
    )

    assert response.status_code == 503
    assert "Legacy email token issuance is disabled" in response.json()["detail"]
