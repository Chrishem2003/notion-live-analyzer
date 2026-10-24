from __future__ import annotations

from sovereign_intelligence.config import BrainConfig
from sovereign_intelligence.providers.registry import ProviderRegistry
from sovereign_intelligence.providers.ollama import OllamaProvider


def test_brain_config_accepts_ollama_provider():
    config = BrainConfig(default_provider="ollama", default_model="qwen2.5:3b")
    assert config.default_provider == "ollama"
    assert config.default_model == "qwen2.5:3b"


def test_registry_registers_ollama_provider():
    registry = ProviderRegistry.default()
    provider = registry.get("ollama")
    assert isinstance(provider, OllamaProvider)
    assert provider.default_model == "qwen2.5:3b"


def test_env_autodetects_ollama_when_explicitly_configured(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.delenv("SOVEREIGN_AI_PROVIDER", raising=False)

    config = BrainConfig.from_env()
    assert config.default_provider == "ollama"
