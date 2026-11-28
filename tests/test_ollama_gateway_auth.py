from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.responses import Response
from fastapi.testclient import TestClient

from ollama_gateway import _authorize, _configured_token, app


def test_gateway_requires_strong_configured_secret(monkeypatch):
    monkeypatch.delenv("OLLAMA_GATEWAY_TOKEN", raising=False)
    with pytest.raises(HTTPException) as exc:
        _configured_token()
    assert exc.value.status_code == 503

    monkeypatch.setenv("OLLAMA_GATEWAY_TOKEN", "too-short")
    with pytest.raises(HTTPException) as exc:
        _configured_token()
    assert exc.value.status_code == 503


def test_gateway_rejects_missing_and_wrong_credentials(monkeypatch):
    monkeypatch.setenv("OLLAMA_GATEWAY_TOKEN", "s" * 48)
    with pytest.raises(HTTPException) as exc:
        _authorize(None)
    assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc:
        _authorize("Bearer incorrect")
    assert exc.value.status_code == 401


def test_gateway_accepts_matching_bearer_token(monkeypatch):
    token = "s" * 48
    monkeypatch.setenv("OLLAMA_GATEWAY_TOKEN", token)
    _authorize(f"Bearer {token}")


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/tags"),
        ("POST", "/api/chat"),
        ("POST", "/api/generate"),
        ("POST", "/api/embeddings"),
    ],
)
def test_gateway_rejects_duplicate_raw_authorization_before_proxy(
    monkeypatch, method, path
):
    token = "s" * 48
    monkeypatch.setenv("OLLAMA_GATEWAY_TOKEN", token)

    async def unexpected_proxy(*args, **kwargs):
        pytest.fail("duplicate Authorization fields must be rejected before proxying")

    monkeypatch.setattr("ollama_gateway._proxy", unexpected_proxy)
    client = TestClient(app)
    headers = [
        ("Authorization", f"Bearer {token}"),
        ("Authorization", f"Bearer {token}"),
    ]
    response = client.request(
        method,
        path,
        headers=headers,
        content=b"{}" if method == "POST" else None,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid gateway credentials."


def test_gateway_accepts_one_raw_authorization_and_uses_proxy(monkeypatch):
    token = "s" * 48
    monkeypatch.setenv("OLLAMA_GATEWAY_TOKEN", token)
    calls = []

    async def fake_proxy(method, path, request):
        calls.append((method, path))
        return Response(content=b"synthetic", status_code=202)

    monkeypatch.setattr("ollama_gateway._proxy", fake_proxy)
    response = TestClient(app).get(
        "/api/tags",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    assert response.content == b"synthetic"
    assert calls == [("GET", "/api/tags")]
