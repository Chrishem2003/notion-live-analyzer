from __future__ import annotations

import os
import httpx

from .base import ModelProvider, ProviderError
from ..models import AIRequest, AIResponse


class OpenAICompatibleProvider(ModelProvider):

    name = "openai-compatible"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url.rstrip("/")

    def generate(self, request: AIRequest) -> AIResponse:

        if not self.api_key:
            raise ProviderError(
                "OPENAI_API_KEY is not configured."
            )

        payload = {
            "model": request.model or "gpt-5",
            "messages": [],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        if request.system:
            payload["messages"].append(
                {"role": "system", "content": request.system}
            )

        payload["messages"].append(
            {"role": "user", "content": request.prompt}
        )

        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120,
            )
            response.raise_for_status()

        except Exception as exc:
            raise ProviderError(str(exc)) from exc

        data = response.json()

        choices = data.get("choices", [])

        if not choices:
            raise ProviderError(
                "Provider returned no choices."
            )

        message = choices[0].get("message", {})

        return AIResponse(
            text=message.get("content", ""),
            provider=self.name,
            model=data.get("model", payload["model"]),
            usage=data.get("usage", {}),
            metadata=data,
        )