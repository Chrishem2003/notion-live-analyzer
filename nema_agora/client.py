"""Server-side, read-only client for the NEMA-AGORA case API."""
from __future__ import annotations
import os
from typing import Any
from urllib.parse import quote, urlparse
import requests

class NemaApiError(RuntimeError):
    """Safe-to-display API error; never includes request headers or secrets."""

def _settings() -> tuple[str, str]:
    base_url = os.getenv("NEMA_CASE_API_BASE_URL", "https://notion-live-analyzer-api.onrender.com").strip().rstrip("/")
    api_key = os.getenv("PLATFORM_API_KEY", "").strip()
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise NemaApiError("NEMA API URL must be a valid HTTPS URL.")
    if not api_key:
        raise NemaApiError("The NEMA API key is not configured for this Streamlit service. Add PLATFORM_API_KEY to the Streamlit service environment.")
    return base_url, api_key

def _get(path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    base_url, api_key = _settings()
    try:
        response = requests.get(f"{base_url}/api/v1/nema/cases{path}", headers={"X-API-Key": api_key, "Accept": "application/json"}, params=params, timeout=(3.05, 12))
    except requests.RequestException as exc:
        raise NemaApiError("The NEMA API could not be reached. Check service health and try again.") from exc
    if response.status_code == 401:
        raise NemaApiError("The API rejected the service credential. Check that both Render services use the same PLATFORM_API_KEY.")
    if response.status_code == 503:
        raise NemaApiError("NEMA case storage is not ready or is temporarily unavailable.")
    if response.status_code == 404 and path != "":
        raise NemaApiError("That case was not found.")
    if not response.ok:
        raise NemaApiError(f"The NEMA API returned HTTP {response.status_code}.")
    try:
        data = response.json()
    except ValueError as exc:
        raise NemaApiError("The NEMA API returned an invalid response.") from exc
    if not isinstance(data, dict):
        raise NemaApiError("The NEMA API returned an unexpected response format.")
    return data

def get_storage_readiness() -> dict[str, Any]:
    return _get("/storage-readiness")

def list_cases(limit: int = 100) -> dict[str, Any]:
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    return _get("", params={"limit": limit})

def get_case(case_id: str) -> dict[str, Any]:
    clean_id = case_id.strip()
    if not clean_id or len(clean_id) > 200:
        raise ValueError("case_id must contain 1–200 non-whitespace characters")
    return _get("/" + quote(clean_id, safe=""))

def get_review_packet(case_id: str) -> dict[str, Any]:
    """Request a deterministic read-only review packet preview for one case."""
    clean_id = case_id.strip()
    if not clean_id or len(clean_id) > 80:
        raise ValueError("case_id must contain 1–80 non-whitespace characters")
    if clean_id != case_id:
        raise ValueError("case_id must not have leading or trailing whitespace")
    return _get("/" + quote(clean_id, safe="") + "/review-packet")
