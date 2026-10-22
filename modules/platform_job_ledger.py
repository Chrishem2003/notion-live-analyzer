"""Server-side RPC client for the Supabase platform job ledger."""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any
from urllib.parse import urlparse

import requests


class PlatformLedgerUnavailable(RuntimeError):
    """The durable job ledger could not complete an operation."""


class PlatformJobLedger:
    def __init__(self, *, session: Any | None = None, timeout: float = 5.0) -> None:
        base_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
        secret = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise PlatformLedgerUnavailable("A valid HTTPS database URL is required.")
        if not secret:
            raise PlatformLedgerUnavailable("Server-side database credentials are not configured.")
        if not 0 < timeout <= 30:
            raise ValueError("timeout must be greater than zero and at most 30 seconds")
        self._base_url = base_url
        self._timeout = timeout
        self._session = session or requests.Session()
        self._session.headers.update({
            "apikey": secret,
            "Authorization": f"Bearer {secret}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def close(self) -> None:
        close = getattr(self._session, "close", None)
        if callable(close):
            close()

    @staticmethod
    def request_hash(payload: dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON object.")
        try:
            body = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("Payload must contain valid JSON values.") from exc
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def _rpc(self, name: str, body: dict[str, Any]) -> Any:
        try:
            response = self._session.post(
                f"{self._base_url}/rest/v1/rpc/{name}",
                json=body,
                timeout=self._timeout,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError, TypeError) as exc:
            raise PlatformLedgerUnavailable(f"Ledger operation '{name}' failed.") from exc

    def enqueue(self, *, job_type: str, actor_scope: str, idempotency_key: str,
                payload: dict[str, Any], max_attempts: int = 3) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON object.")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("A stable idempotency key is required.")
        value = self._rpc("platform_enqueue_job", {
            "p_job_type": job_type,
            "p_actor_scope": actor_scope,
            "p_idempotency_key": idempotency_key,
            "p_request_hash": self.request_hash(payload),
            "p_payload": payload,
            "p_max_attempts": max_attempts,
        })
        if not isinstance(value, dict) or not value.get("job_id") or value.get("status") not in {
            "queued", "running", "succeeded", "failed", "needs_review"
        }:
            raise PlatformLedgerUnavailable("Ledger returned an invalid enqueue response.")
        return value

    def claim(self, *, worker_id: str, lease_seconds: int = 120) -> dict[str, Any] | None:
        value = self._rpc("platform_claim_job", {
            "p_worker_id": worker_id,
            "p_lease_seconds": lease_seconds,
        })
        if value is None:
            return None
        if (not isinstance(value, dict)
                or not all(value.get(k) for k in ("job_id", "job_type", "lease_token"))
                or not isinstance(value.get("payload"), dict)):
            raise PlatformLedgerUnavailable("Ledger returned an invalid claim response.")
        return value

    def finish(self, *, job_id: str, worker_id: str, lease_token: str, status: str,
               result: dict[str, Any] | None = None,
               error: dict[str, Any] | None = None) -> dict[str, Any]:
        if status not in {"succeeded", "failed", "needs_review"}:
            raise ValueError("Unsupported terminal status.")
        if result is not None and not isinstance(result, dict):
            raise ValueError("Result must be an object or None.")
        if error is not None and not isinstance(error, dict):
            raise ValueError("Error must be an object or None.")
        value = self._rpc("platform_finish_job", {
            "p_job_id": job_id,
            "p_worker_id": worker_id,
            "p_lease_token": lease_token,
            "p_status": status,
            "p_result": result,
            "p_error": error,
        })
        if not isinstance(value, dict) or value.get("job_id") != job_id:
            raise PlatformLedgerUnavailable("Ledger returned an invalid finish response.")
        return value
