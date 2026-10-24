from __future__ import annotations

import os
import httpx

from .base import ModelProvider, ProviderError
from ..models import AIRequest, AIResponse


class OllamaProvider(ModelProvider):
    """Local Ollama chat provider; no cloud API key is required."""

    name = "ollama"
    default_model = "qwen2.5:3b"

    def __init__(self, base_url: str | None = None, timeout: float = 120.0):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        """Use a server-side bearer token when talking to a protected remote gateway."""
        token = os.getenv("OLLAMA_API_KEY", "").strip()
        return {"Authorization": f"Bearer {token}"} if token else {}

    def is_available(self) -> bool:
        try:
            response = httpx.get(
                f"{self.base_url}/api/tags", headers=self._headers(), timeout=2.0
            )
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def generate(self, request: AIRequest) -> AIResponse:
        model = (request.model or os.getenv("OLLAMA_MODEL") or self.default_model).strip()
        messages: list[dict[str, str]] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
                },
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(
                "Ollama request failed. Check that Ollama is running, the model exists, and OLLAMA_BASE_URL is correct."
            ) from exc
        message = data.get("message") or {}
        answer = message.get("content")
        if not isinstance(answer, str) or not answer.strip():
            raise ProviderError("Ollama returned an empty chat response.")
        usage = {key: data[key] for key in ("prompt_eval_count", "eval_count", "total_duration") if key in data}
        return AIResponse(
            text=answer.strip(),
            provider=self.name,
            model=data.get("model") or model,
            usage=usage,
            metadata={"done": data.get("done", False)},
        )
