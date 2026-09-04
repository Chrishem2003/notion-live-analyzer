from __future__ import annotations

import os
from dataclasses import dataclass


# Priority order used only when SOVEREIGN_AI_PROVIDER is not set explicitly.
# Each entry is (provider name, the env var that proves it's actually usable).
_PROVIDER_KEY_ENV = (
    ("anthropic", "ANTHROPIC_API_KEY"),
    ("openai", "OPENAI_API_KEY"),
    ("openrouter", "OPENROUTER_API_KEY"),
    ("google", "GOOGLE_API_KEY"),
)


def _autodetect_provider() -> str:
    """Pick the first provider whose API key is actually configured.

    Falls back to "openai" (the original hardcoded default) if none of the
    provider keys are set, so behavior for a fully-unconfigured deployment
    is unchanged - it still fails with a clear "not configured" error from
    that provider rather than silently doing nothing.
    """
    for provider_name, env_var in _PROVIDER_KEY_ENV:
        if os.getenv(env_var):
            return provider_name
    return "openai"


@dataclass
class BrainConfig:
    default_provider: str = "openai"
    # Left blank by default so each provider's own sensible built-in model
    # (e.g. AnthropicProvider defaults to "claude-sonnet-4-5",
    # GoogleProvider to "gemini-2.5-flash") is used instead of forcing
    # every provider to receive OpenAI's "gpt-5" regardless of who's
    # actually configured. Set SOVEREIGN_AI_MODEL to override explicitly.
    default_model: str = ""
    fallback_provider: str | None = None
    temperature: float = 0.2
    max_tokens: int = 4096
    memory_path: str = "data/sovereign_intelligence/memory.db"
    audit_path: str = "data/sovereign_intelligence/audit.jsonl"
    enable_verification: bool = True
    max_iterations: int = 4
    enable_adaptive_execution: bool = True

    @classmethod
    def from_env(cls) -> "BrainConfig":
        return cls(
            default_provider=os.getenv(
                "SOVEREIGN_AI_PROVIDER", _autodetect_provider()
            ),
            default_model=os.getenv("SOVEREIGN_AI_MODEL", ""),
            fallback_provider=os.getenv("SOVEREIGN_AI_FALLBACK_PROVIDER"),
            temperature=float(os.getenv("SOVEREIGN_AI_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("SOVEREIGN_AI_MAX_TOKENS", "4096")),
            memory_path=os.getenv(
                "SOVEREIGN_AI_MEMORY_PATH",
                "data/sovereign_intelligence/memory.db",
            ),
            audit_path=os.getenv(
                "SOVEREIGN_AI_AUDIT_PATH",
                "data/sovereign_intelligence/audit.jsonl",
            ),
            enable_verification=os.getenv(
                "SOVEREIGN_AI_VERIFICATION", "true"
            ).lower() == "true",
            max_iterations=int(
                os.getenv("SOVEREIGN_AI_MAX_ITERATIONS", "4")
            ),
            enable_adaptive_execution=os.getenv(
                "SOVEREIGN_AI_ADAPTIVE_EXECUTION",
                "true",
            ).lower() == "true",
        )