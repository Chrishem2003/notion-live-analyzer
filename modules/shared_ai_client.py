"""Server-side client for the shared AI API.

Only call this from authenticated Streamlit server code. The platform API key
is never sent to the browser or returned to the caller.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse

import requests


class SharedAIError(RuntimeError):
    """Safe-to-display shared AI client error."""


def request_shared_ai(*, product: str, task: str, input_text: str, user_email: str) -> dict:
    base_url = os.getenv("SHARED_AI_API_URL", "").strip().rstrip("/")
    api_key = os.getenv("PLATFORM_API_KEY", "").strip()
    email = user_email.strip().lower()

    if not base_url or not api_key or not email:
        raise SharedAIError("Shared AI is not configured for this signed-in session.")

    parsed = urlparse(base_url)
    local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not local_http:
        raise SharedAIError("Shared AI endpoint must use HTTPS.")

    try:
        token_response = requests.post(
            f"{base_url}/api/v1/chat/token",
            params={"email": email},
            headers={"X-API-Key": api_key},
            timeout=8,
        )
    except requests.RequestException:
        raise SharedAIError("Shared AI authentication service is unreachable.")
    if token_response.status_code != 200:
        raise SharedAIError("Shared AI could not authenticate this session. Check the API service configuration.")
    try:
        token = token_response.json().get("token")
    except (ValueError, AttributeError):
        token = None
    if not isinstance(token, str) or not token:
        raise SharedAIError("Shared AI authentication did not return a valid session token.")

    try:
        response = requests.post(
            f"{base_url}/api/v1/ai/respond",
            headers={"Authorization": f"Bearer {token}"},
            json={"product": product, "task": task, "input": input_text},
            timeout=45,
        )
    except requests.RequestException:
        raise SharedAIError("Shared AI service is unreachable.")
    if response.status_code != 200:
        if response.status_code == 503:
            raise SharedAIError("Shared AI is not enabled yet or a required server setting is missing.")
        if response.status_code == 401:
            raise SharedAIError("Shared AI rejected the user session. Please sign in again.")
        raise SharedAIError(f"Shared AI request failed (HTTP {response.status_code}).")
    try:
        result = response.json()
    except ValueError:
        raise SharedAIError("Shared AI returned an invalid response.")
    if not isinstance(result, dict) or not isinstance(result.get("output"), str):
        raise SharedAIError("Shared AI response did not contain an answer.")
    return result
