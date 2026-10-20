"""Minimal client for the authenticated Bio-Research run-writeback API.

The client deliberately does not auto-retry POST requests. If a response is
ambiguous, the user must retry with the same run_id so the server-side
idempotency ledger can reconcile the outcome.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests


class ResearchRunClientError(RuntimeError):
    """The research-run API rejected the request or could not be reached."""


class ResearchRunClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 20.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("RESEARCH_RUN_API_URL must be configured.")
        parsed = urlparse(base_url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Research-run API URL must be an absolute HTTP(S) URL.")
        if not api_key or not api_key.strip():
            raise ValueError("PLATFORM_API_KEY must be configured server-side.")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero.")
        self.endpoint = base_url.strip().rstrip("/") + "/api/v1/research-runs"
        self.api_key = api_key.strip()
        self.timeout = timeout
        self.session = session or requests.Session()

    def create_run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dictionary.")
        try:
            response = self.session.post(
                self.endpoint,
                json=payload,
                headers={
                    "X-API-Key": self.api_key,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise ResearchRunClientError(
                "The API response was not received. Do not generate a new run_id; "
                "check the server and retry with the same run_id."
            ) from exc
        except requests.RequestException as exc:
            raise ResearchRunClientError(
                f"Research-run API request failed ({type(exc).__name__})."
            ) from exc

        if not 200 <= response.status_code < 300:
            try:
                body = response.json()
                detail = body.get("detail", body.get("message", "Request rejected"))
            except (ValueError, AttributeError):
                detail = "Request rejected"
            if isinstance(detail, (dict, list)):
                detail = str(detail)
            raise ResearchRunClientError(
                f"Research-run API returned HTTP {response.status_code}: {str(detail)[:600]}"
            )
        try:
            result = response.json()
        except ValueError as exc:
            raise ResearchRunClientError("Research-run API returned invalid JSON.") from exc
        if not isinstance(result, dict) or not result.get("run_id") or not result.get("page_id"):
            raise ResearchRunClientError("API response is missing the run_id or persisted page_id.")
        return result
