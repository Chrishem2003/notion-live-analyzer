"""Server-side client for the shared AI API.

Pass the access token from the currently authenticated Supabase session. The
token must be held in server-side Streamlit session state, never in a URL,
browser local storage, logs, or client-visible configuration. The API verifies
the token with Supabase Auth and derives the actor from the verified user ID.
"""
from __future__ import annotations

import os
import uuid
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


def _user_jobs_request(method: str, path: str, *, access_token: str, json_body=None, idempotency_key=None):
    """Call the opt-in user-scoped job API with a verified Supabase bearer token."""
    base_url = os.getenv("SHARED_AI_API_URL", "").strip().rstrip("/")
    token = access_token.strip() if isinstance(access_token, str) else ""
    if not base_url or not token:
        raise SharedAIError("User jobs are not configured for this signed-in session.")
    parsed = urlparse(base_url)
    local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not local_http:
        raise SharedAIError("User job endpoint must use HTTPS.")
    headers = {"Authorization": f"Bearer {token}"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    try:
        response = requests.request(
            method, f"{base_url}/api/v1/user-jobs{path}",
            headers=headers, json=json_body, timeout=30,
        )
    except requests.RequestException:
        raise SharedAIError("User job service is unreachable.") from None
    if response.status_code not in ({202, 200} if method == "POST" else {200}):
        if response.status_code == 401:
            raise SharedAIError("User job service rejected this session. Please sign in again.")
        if response.status_code == 404:
            raise SharedAIError("Job not found for this account.")
        if response.status_code == 409:
            raise SharedAIError("This job cannot be changed now or the idempotency key conflicts.")
        if response.status_code == 422:
            raise SharedAIError("The job request was not accepted. Check the input and try again.")
        if response.status_code == 429:
            raise SharedAIError("Your job quota has been reached. Please retry later.")
        if response.status_code == 503:
            raise SharedAIError("Per-user jobs are disabled or the authentication/storage service is unavailable.")
        raise SharedAIError(f"User job request failed (HTTP {response.status_code}).")
    try:
        payload = response.json()
    except ValueError:
        raise SharedAIError("User job service returned an invalid response.") from None
    if not isinstance(payload, dict):
        raise SharedAIError("User job service returned an invalid response.")
    return payload


def request_user_job(*, prompt: str, access_token: str, provider: str | None = None,
                     model: str | None = None, strategy: str = "direct",
                     idempotency_key: str | None = None) -> dict:
    text = prompt.strip() if isinstance(prompt, str) else ""
    if not text or len(text) > 12000:
        raise SharedAIError("Describe the job in 1–12,000 characters.")
    key = idempotency_key or str(uuid.uuid4())
    result = _user_jobs_request(
        "POST", "", access_token=access_token,
        json_body={"job_type": "intelligence.solve", "prompt": text,
                   "provider": provider, "model": model, "strategy": strategy},
        idempotency_key=key,
    )
    if not isinstance(result.get("job_id"), str) or result.get("status") != "queued":
        raise SharedAIError("User job service did not confirm a queued job.")
    result["client_idempotency_key"] = key
    return result


def _validated_job_id(job_id: str) -> str:
    if not isinstance(job_id, str) or not job_id.strip():
        raise SharedAIError("Enter a job ID first.")
    try:
        return str(uuid.UUID(job_id.strip()))
    except (ValueError, TypeError, AttributeError):
        raise SharedAIError("Job ID must be a valid UUID.") from None


def get_user_job(*, job_id: str, access_token: str) -> dict:
    safe_job_id = _validated_job_id(job_id)
    return _user_jobs_request("GET", f"/{safe_job_id}", access_token=access_token)


def cancel_user_job(*, job_id: str, access_token: str) -> dict:
    safe_job_id = _validated_job_id(job_id)
    result = _user_jobs_request("DELETE", f"/{safe_job_id}", access_token=access_token)
    if result.get("status") != "cancelled":
        raise SharedAIError("The service did not confirm job cancellation.")
    return result
