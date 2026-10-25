"""Server-side client for the shared AI API.

Pass the access token from the currently authenticated Supabase session. The
token must be held in server-side Streamlit session state, never in a URL,
browser local storage, logs, or client-visible configuration. The API verifies
the token with Supabase Auth and derives the actor from the verified user ID.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse

import requests


class SharedAIError(RuntimeError):
    """Safe-to-display shared AI client error."""


def request_shared_ai(
    *,
    product: str,
    task: str,
    input_text: str,
    access_token: str,
) -> dict:
    base_url = os.getenv("SHARED_AI_API_URL", "").strip().rstrip("/")
    token = access_token.strip() if isinstance(access_token, str) else ""

    if not base_url or not token:
        raise SharedAIError("Shared AI is not configured for this signed-in session.")

    parsed = urlparse(base_url)
    local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not local_http:
        raise SharedAIError("Shared AI endpoint must use HTTPS.")

    try:
        response = requests.post(
            f"{base_url}/api/v1/ai/respond",
            headers={"Authorization": f"Bearer {token}"},
            json={"product": product, "task": task, "input": input_text},
            timeout=45,
        )
    except requests.RequestException:
        raise SharedAIError("Shared AI service is unreachable.") from None
    if response.status_code != 200:
        if response.status_code == 503:
            raise SharedAIError("Shared AI is not enabled yet or a required server setting is missing.")
        if response.status_code == 401:
            raise SharedAIError("Shared AI rejected the user session. Please sign in again.")
        if response.status_code == 429:
            raise SharedAIError("Shared AI request limit reached. Please wait before retrying.")
        raise SharedAIError(f"Shared AI request failed (HTTP {response.status_code}).")
    try:
        result = response.json()
    except ValueError:
        raise SharedAIError("Shared AI returned an invalid response.") from None
    if not isinstance(result, dict) or not isinstance(result.get("output"), str):
        raise SharedAIError("Shared AI response did not contain an answer.")
    return result


def request_automation_draft(*, description: str, access_token: str) -> dict:
    """Request a schema-validated automation proposal; never execute it."""
    base_url = os.getenv("SHARED_AI_API_URL", "").strip().rstrip("/")
    token = access_token.strip() if isinstance(access_token, str) else ""
    text = description.strip() if isinstance(description, str) else ""
    if not base_url or not token:
        raise SharedAIError("Shared AI is not configured for this signed-in session.")
    if not text or len(text) > 12000:
        raise SharedAIError("Describe the automation in 1–12,000 characters.")
    parsed = urlparse(base_url)
    local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not local_http:
        raise SharedAIError("Shared AI endpoint must use HTTPS.")
    try:
        response = requests.post(
            f"{base_url}/api/v1/automations/draft",
            headers={"Authorization": f"Bearer {token}"},
            json={"description": text},
            timeout=60,
        )
    except requests.RequestException:
        raise SharedAIError("Shared AI service is unreachable.") from None
    if response.status_code != 200:
        if response.status_code == 503:
            raise SharedAIError("Shared AI is not enabled yet or a required server setting is missing.")
        if response.status_code == 401:
            raise SharedAIError("Shared AI rejected the user session. Please sign in again.")
        if response.status_code == 429:
            raise SharedAIError("Request limit reached. Please wait before retrying.")
        if response.status_code == 502:
            raise SharedAIError("The automation draft failed validation. Refine the description and try again.")
        raise SharedAIError(f"Automation draft request failed (HTTP {response.status_code}).")
    try:
        result = response.json()
    except ValueError:
        raise SharedAIError("Shared AI returned an invalid automation draft.") from None
    draft = result.get("draft") if isinstance(result, dict) else None
    if (
        not isinstance(draft, dict)
        or not isinstance(draft.get("title"), str)
        or not isinstance(draft.get("steps"), list)
        or result.get("executed") is not False
        or result.get("status") != "draft_only"
        or draft.get("approval_required") is not True
        or draft.get("risk_level") not in {"low", "medium", "high"}
    ):
        raise SharedAIError("Automation draft did not meet the safe proposal contract.")
    for step in draft["steps"]:
        if not isinstance(step, dict) or step.get("requires_approval") is not True:
            raise SharedAIError("Automation draft contains a step without an approval gate.")
    return result
