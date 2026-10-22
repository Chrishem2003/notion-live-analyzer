from __future__ import annotations

import pytest

from sovereign_intelligence.config import BrainConfig


@pytest.mark.parametrize("provider", ["openai", "openrouter", "anthropic", "google", " OPENAI "])
def test_supported_provider_names_are_normalized(provider):
    config = BrainConfig(default_provider=provider)
    assert config.default_provider == provider.strip().lower()


@pytest.mark.parametrize("provider", ["", "unknown", "ollama", "google-genai", None])
def test_unknown_provider_is_rejected(provider):
    with pytest.raises(ValueError, match="supported provider"):
        BrainConfig(default_provider=provider)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"temperature": -0.01}, "temperature"),
        ({"temperature": float("nan")}, "temperature"),
        ({"temperature": float("inf")}, "temperature"),
        ({"temperature": True}, "temperature"),
        ({"max_tokens": 0}, "max_tokens"),
        ({"max_tokens": -1}, "max_tokens"),
        ({"max_tokens": True}, "max_tokens"),
        ({"max_iterations": 0}, "max_iterations"),
        ({"max_iterations": 11}, "max_iterations"),
        ({"memory_path": "  "}, "memory_path"),
        ({"audit_path": ""}, "audit_path"),
    ],
)
def test_invalid_runtime_limits_and_paths_fail_closed(kwargs, message):
    with pytest.raises(ValueError, match=message):
        BrainConfig(**kwargs)


def test_fallback_provider_is_validated():
    with pytest.raises(ValueError, match="fallback_provider"):
        BrainConfig(fallback_provider="not-a-provider")


def test_environment_boolean_parser_rejects_typo(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_AI_VERIFICATION", "tru")
    with pytest.raises(ValueError, match="SOVEREIGN_AI_VERIFICATION"):
        BrainConfig.from_env()


def test_environment_boolean_parser_accepts_explicit_false(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_AI_VERIFICATION", "false")
    monkeypatch.setenv("SOVEREIGN_AI_ADAPTIVE_EXECUTION", "0")
    config = BrainConfig.from_env()
    assert config.enable_verification is False
    assert config.enable_adaptive_execution is False


def test_provider_autodetection_ignores_whitespace_keys(monkeypatch):
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-only-key")
    assert BrainConfig.from_env().default_provider == "google"
