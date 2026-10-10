from __future__ import annotations
import os

from .base import ModelProvider
from .openai import OpenAIProvider
from .openrouter import OpenRouterProvider
from .anthropic import AnthropicProvider
from .google import GoogleProvider


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

        return registry

    def configured_names(self) -> list[str]:
        """
        Return providers that currently have credentials configured.

        This never returns or logs credential values.
        """
        names = []

        environment_keys = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }

        for name in self._providers:
            key = environment_keys.get(name)
            if key and os.getenv(key):
                names.append(name)

        return sorted(names)

    def as_dict(self) -> dict[str, ModelProvider]:
        return dict(self._providers)
