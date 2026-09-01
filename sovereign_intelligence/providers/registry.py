from __future__ import annotations

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