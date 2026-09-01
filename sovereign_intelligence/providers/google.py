from __future__ import annotations

import os
import httpx

from .base import ModelProvider, ProviderError
from ..models import AIRequest, AIResponse


class GoogleProvider(ModelProvider):

    name = "google"

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")

    def generate(self, request: AIRequest) -> AIResponse:

        if not self.api_key:
            raise ProviderError(
                "GOOGLE_API_KEY is not configured."
            )

        model = request.model or "gemini-2.5-flash"

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model}:generateContent"
            f"?key={self.api_key}"
        )

        contents = [
            {
                "role": "user",
                "parts": [
                    {"text": request.prompt}
                ],
            }
        ]

        if request.system:
            contents.insert(
                0,
                {
                    "role": "user",
                    "parts": [
                        {"text": request.system}
                    ],
                },
            )

        try:
            response = httpx.post(
                url,
                json={"contents": contents},
                timeout=120,
            )
            response.raise_for_status()

        except Exception as exc:
            raise ProviderError(str(exc)) from exc

        data = response.json()

        candidates = data.get("candidates", [])

        if not candidates:
            raise ProviderError(
                "Google returned no candidates."
            )

        parts = (
            candidates[0]
            .get("content", {})
            .get("parts", [])
        )

        text = "".join(
            part.get("text", "")
            for part in parts
        )

        return AIResponse(
            text=text,
            provider=self.name,
            model=model,
            metadata=data,
        )