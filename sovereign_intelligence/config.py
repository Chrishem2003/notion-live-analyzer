from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class BrainConfig:
    default_provider: str = "openai"
    default_model: str = "gpt-5"
    fallback_provider: str | None = None
    temperature: float = 0.2
    max_tokens: int = 4096
    memory_path: str = "data/sovereign_intelligence/memory.db"
    audit_path: str = "data/sovereign_intelligence/audit.jsonl"
    enable_verification: bool = True
    max_iterations: int = 4

    @classmethod
    def from_env(cls) -> "BrainConfig":
        return cls(
            default_provider=os.getenv("SOVEREIGN_AI_PROVIDER", "openai"),
            default_model=os.getenv("SOVEREIGN_AI_MODEL", "gpt-5"),
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
        )