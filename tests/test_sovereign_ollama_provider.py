from __future__ import annotations

import httpx
import pytest

from sovereign_intelligence.models import AIRequest
from sovereign_intelligence.providers.base import ProviderError
from sovereign_intelligence.providers.ollama import OllamaProvider


def test_ollama_provider_sends_chat_request(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "model": "qwen2.5:3b",
                "message": {"role": "assistant", "content": "LOCAL BRAIN READY"},
                "done": True,
                "prompt_eval_count": 12,
                "eval_count": 4,
            }

    def fake_post(url, *, json, timeout):
        captured.update(url=url, payload=json, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = OllamaProvider(base_url="http://127.0.0.1:11434")
    result = provider.generate(
        AIRequest(prompt="Say ready", system="Be concise", temperature=0.1, max_tokens=50)
    )

    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
    assert captured["payload"]["model"] == "qwen2.5:3b"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["messages"] == [
        {"role": "system", "content": "Be concise"},
        {"role": "user", "content": "Say ready"},
    ]
    assert result.text == "LOCAL BRAIN READY"
    assert result.provider == "ollama"
    assert result.model == "qwen2.5:3b"
    assert result.usage["eval_count"] == 4


def test_ollama_provider_rejects_empty_response(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"model": "qwen2.5:3b", "message": {"content": ""}}

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: FakeResponse())
    with pytest.raises(ProviderError, match="empty chat response"):
        OllamaProvider().generate(AIRequest(prompt="Say ready"))


def test_ollama_provider_wraps_connection_error(monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", fail)
    with pytest.raises(ProviderError, match="Ollama request failed"):
        OllamaProvider().generate(AIRequest(prompt="Say ready"))
