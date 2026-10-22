from __future__ import annotations

import httpx

from sovereign_intelligence.models import AIRequest
from sovereign_intelligence.providers.anthropic import AnthropicProvider
from sovereign_intelligence.providers.google import GoogleProvider
from sovereign_intelligence.providers.openai import OpenAIProvider
from sovereign_intelligence.providers.openrouter import OpenRouterProvider
from sovereign_intelligence.providers.registry import ProviderRegistry


def test_each_provider_exposes_its_own_default_model(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    registry = ProviderRegistry.default()

    assert registry.get("openai").default_model == "gpt-5"
    assert registry.get("openrouter").default_model == "openai/gpt-5"
    assert registry.get("anthropic").default_model == "claude-sonnet-4-5"
    assert registry.get("google").default_model == "gemini-2.5-flash"


def test_openrouter_uses_qualified_default_model_without_network(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only-key")
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "model": "openai/gpt-5",
                "choices": [{"message": {"content": "deterministic test response"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }

    def fake_post(url, *, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)

    response = OpenRouterProvider().generate(AIRequest(prompt="test prompt"))

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["payload"]["model"] == "openai/gpt-5"
    assert response.text == "deterministic test response"
    assert response.provider == "openrouter"
