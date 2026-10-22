from __future__ import annotations

import math
import os
from dataclasses import dataclass


SUPPORTED_PROVIDERS = frozenset({"openai", "openrouter", "anthropic", "google"})

# Priority order used only when SOVEREIGN_AI_PROVIDER is not set explicitly.
_PROVIDER_KEY_ENV = (
    ("anthropic", "ANTHROPIC_API_KEY"),
    ("openai", "OPENAI_API_KEY"),
    ("openrouter", "OPENROUTER_API_KEY"),
    ("google", "GOOGLE_API_KEY"),
)


def _autodetect_provider() -> str:
    """Select the first supported provider whose API key is configured."""
    for provider_name, env_var in _PROVIDER_KEY_ENV:
        if os.getenv(env_var, "").strip():
            return provider_name
    # Preserve a clear unconfigured default; provider invocation will report
    # missing credentials instead of silently disabling AI functionality.
    return "openai"


def _env_bool(name: str, default: bool) -> bool:
    """Parse explicit boolean environment values and reject typos."""
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"true", "1", "yes", "on"}:
        return True
    if value in {"false", "0", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value (true/false).")


@dataclass
class BrainConfig:
    default_provider: str = "openai"
    # Blank model values intentionally defer to the selected provider's default.
    default_model: str = ""
    fallback_provider: str | None = None
    fallback_model: str | None = None
    temperature: float = 0.2
    max_tokens: int = 4096
    memory_path: str = "data/sovereign_intelligence/memory.db"
    audit_path: str = "data/sovereign_intelligence/audit.jsonl"
    enable_verification: bool = True
    max_iterations: int = 4
    enable_adaptive_execution: bool = True

    def __post_init__(self) -> None:
        self.default_provider = self._provider(self.default_provider, "default_provider")
        if self.fallback_provider is not None:
            if not isinstance(self.fallback_provider, str) or not self.fallback_provider.strip():
                raise ValueError("fallback_provider must be a supported provider or None.")
            self.fallback_provider = self._provider(self.fallback_provider, "fallback_provider")

        for field_name in ("default_model", "fallback_model"):
            value = getattr(self, field_name)
            if value is None and field_name == "fallback_model":
                continue
            if not isinstance(value, str):
                raise ValueError(f"{field_name} must be a string.")
            setattr(self, field_name, value.strip())

        if (
            isinstance(self.temperature, bool)
            or not isinstance(self.temperature, (int, float))
            or not math.isfinite(float(self.temperature))
            or not 0 <= float(self.temperature) <= 2
        ):
            raise ValueError("temperature must be a finite number between 0 and 2.")
        if (
            isinstance(self.max_tokens, bool)
            or not isinstance(self.max_tokens, int)
            or not 1 <= self.max_tokens <= 131072
        ):
            raise ValueError("max_tokens must be an integer between 1 and 131072.")
        if (
            isinstance(self.max_iterations, bool)
            or not isinstance(self.max_iterations, int)
            or not 1 <= self.max_iterations <= 10
        ):
            raise ValueError("max_iterations must be an integer between 1 and 10.")

        for field_name in ("memory_path", "audit_path"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty path.")
            setattr(self, field_name, value.strip())

        for field_name in ("enable_verification", "enable_adaptive_execution"):
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"{field_name} must be a boolean.")

    @staticmethod
    def _provider(value: str, field_name: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a supported provider name.")
        provider = value.strip().lower()
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"{field_name} must be one of: {', '.join(sorted(SUPPORTED_PROVIDERS))}."
            )
        return provider

    @classmethod
    def from_env(cls) -> "BrainConfig":
        return cls(
            default_provider=os.getenv("SOVEREIGN_AI_PROVIDER", _autodetect_provider()),
            default_model=os.getenv("SOVEREIGN_AI_MODEL", ""),
            fallback_provider=os.getenv("SOVEREIGN_AI_FALLBACK_PROVIDER") or None,
            fallback_model=os.getenv("SOVEREIGN_AI_FALLBACK_MODEL") or None,
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
            enable_verification=_env_bool("SOVEREIGN_AI_VERIFICATION", True),
            max_iterations=int(os.getenv("SOVEREIGN_AI_MAX_ITERATIONS", "4")),
            enable_adaptive_execution=_env_bool(
                "SOVEREIGN_AI_ADAPTIVE_EXECUTION", True
            ),
        )
