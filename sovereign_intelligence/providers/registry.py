from __future__ import annotations
import os

from .base import ModelProvider
from .openai import OpenAIProvider
from .openrouter import OpenRouterProvider
from .anthropic import AnthropicProvider
from .google import GoogleProvider
from .ollama import OllamaProvider


class ProviderRegistry:

    def __init__(self):
        self._providers: dict[str, ModelProvider] = {}

    def register(
        self,
        provider: ModelProvider,
    ) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> ModelProvider:

        if name not in self._providers:
            raise KeyError(
                f"Provider not registered: {name}"
            )

        return self._providers[name]

    @classmethod
    def default(cls) -> "ProviderRegistry":

        registry = cls()

        registry.register(OpenAIProvider())
        registry.register(OpenRouterProvider())
        registry.register(AnthropicProvider())
        registry.register(GoogleProvider())
        registry.register(OllamaProvider())

        return registry

    def configured_names(self) -> list[str]:
        """
        Return registered cloud providers with credentials and local Ollama
        when reachable. Credential values are never returned or logged.
        """
        names = []

        environment_keys = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }

        for name, key in environment_keys.items():
            # Do not advertise a provider that this registry cannot serve.
            if name in self._providers and os.getenv(key, "").strip():
                names.append(name)

        ollama = self._providers.get("ollama")
        if ollama is not None and callable(getattr(ollama, "is_available", None)):
            if ollama.is_available():
                names.append("ollama")

        return sorted(names)

    def as_dict(self) -> dict[str, ModelProvider]:
        return dict(self._providers)
