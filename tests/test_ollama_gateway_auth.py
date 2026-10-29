from __future__ import annotations

import pytest
from fastapi import HTTPException

from ollama_gateway import _authorize, _configured_token


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
