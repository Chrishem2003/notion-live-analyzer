from __future__ import annotations

from sovereign_intelligence.providers.registry import ProviderRegistry


def test_configured_names_ignore_whitespace_only_keys(monkeypatch):
    for key in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "   ")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "\t")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-placeholder")
    registry = ProviderRegistry()
    registry._providers = {
        "openai": object(),
        "anthropic": object(),
        "google": object(),
        "openrouter": object(),
    }

    assert registry.configured_names() == ["google"]


def test_configured_names_never_return_key_values(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "do-not-return-this-secret")
    registry = ProviderRegistry()
    registry._providers = {"openai": object()}

    names = registry.configured_names()

    assert names == ["openai"]
    assert "do-not-return-this-secret" not in repr(names)
