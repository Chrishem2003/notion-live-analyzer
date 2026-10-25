from __future__ import annotations

from urllib.parse import urlsplit

import httpx


class IntelligenceServiceError(RuntimeError):
    """Safe, user-displayable error from the shared intelligence service."""


class IntelligenceServiceClient:
    """Server-side client for the authenticated platform intelligence API."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 45.0) -> None:
        parsed = urlsplit((base_url or "").strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("INTELLIGENCE_API_URL must be an absolute HTTP(S) URL.")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("INTELLIGENCE_API_URL must not contain credentials, query parameters, or fragments.")
        if not (api_key or "").strip():
            raise ValueError("PLATFORM_API_KEY is required for the shared intelligence service.")
        self.base_url = base_url.strip().rstrip("/")
        self.headers = {"X-API-Key": api_key.strip(), "Accept": "application/json"}
        self.timeout = timeout

    def providers(self) -> dict:
        return self._request("GET", "/api/v1/intelligence/providers")

    def solve(
        self,
        prompt: str,
        provider: str | None = None,
        model: str | None = None,
        strategy: str = "direct",
    ) -> dict:
        clean_prompt = (prompt or "").strip()
        if not clean_prompt:
            raise ValueError("A non-empty prompt is required.")
        payload = {"prompt": clean_prompt, "provider": provider, "model": model, "strategy": strategy}
        result = self._request("POST", "/api/v1/intelligence/solve", json=payload)
        if not isinstance(result.get("answer"), str) or not result["answer"].strip():
            raise IntelligenceServiceError("The intelligence service returned no answer.")
        return result

    def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers=self.headers,
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as exc:
            raise IntelligenceServiceError("The intelligence service timed out. Please retry.") from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code in {401, 403}:
                message = "The intelligence service rejected its server-side credentials."
            elif status_code == 503:
                message = "The intelligence service is not configured or is temporarily unavailable."
            elif status_code == 422:
                message = "The intelligence request was rejected by input validation."
            else:
                message = f"The intelligence service returned HTTP {status_code}."
            raise IntelligenceServiceError(message) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise IntelligenceServiceError("Could not reach the intelligence service or read its response.") from exc
        if not isinstance(data, dict):
            raise IntelligenceServiceError("The intelligence service returned an invalid response.")
        return data
