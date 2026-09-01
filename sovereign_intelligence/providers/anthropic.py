from __future__ import annotations

import os
import httpx

from .base import ModelProvider, ProviderError
from ..models import AIRequest, AIResponse


class AnthropicProvider(ModelProvider):

    name = "anthropic"

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

    def generate(self, request: AIRequest) -> AIResponse:

        if not self.api_key:
            raise ProviderError(
                "ANTHROPIC_API_KEY is not configured."
            )

        payload = {
            "model": request.model or "claude-sonnet-4-5",
            "max_tokens": request.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": request.prompt,
                }
            ],
        }

        if request.system:
            payload["system"] = request.system

        try:
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
                timeout=120,
            )
            response.raise_for_status()

        except Exception as exc:
            raise ProviderError(str(exc)) from exc

        data = response.json()

        parts = data.get("content", [])

        text = "".join(
            part.get("text", "")
            for part in parts
            if part.get("type") == "text"
        )

        return AIResponse(
            text=text,
            provider=self.name,
            model=data.get("model", payload["model"]),
            usage=data.get("usage", {}),
            metadata=data,
        )