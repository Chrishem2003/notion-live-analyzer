"""Supabase PostgREST repository for durable platform jobs.

This repository is service-to-service only. Do not expose its shared API-key
routes directly to browsers or treat the service identity as a user identity.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any
from urllib.parse import urlparse

import requests


class JobStoreUnavailable(RuntimeError):
    """The durable job store is not configured or did not respond safely."""


class JobConflict(RuntimeError):
    """An idempotency key was reused with a different payload."""


class SupabaseJobRepository:
    def __init__(self, *, session: Any | None = None, timeout: float = 8.0) -> None:
        base_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
        service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc or not service_key:
            raise JobStoreUnavailable("Durable job storage is not configured.")
        self.base_url = base_url
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def close(self) -> None:
        close = getattr(self.session, "close", None)
        if callable(close):
            close()

    @staticmethod
    def fingerprint(payload: dict[str, Any]) -> str:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self.session.request(method, f"{self.base_url}/rest/v1/{path}", timeout=self.timeout, **kwargs)
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return None
            return response.json()
        except requests.RequestException as exc:
            # Never forward provider/database response bodies or credentials.
            raise JobStoreUnavailable("Durable job storage request failed.") from exc
        except ValueError as exc:
            raise JobStoreUnavailable("Durable job storage returned invalid data.") from exc

    def enqueue(self, *, idempotency_key: str, job_type: str, payload: dict[str, Any], max_attempts: int = 3, tenant_id: str = "platform-service", requested_by: str = "trusted-service-api") -> dict[str, Any]:
        key = idempotency_key.strip()
        if not key or len(key) > 200 or not re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", key):
            raise ValueError("Idempotency key must use 1–200 letters, digits, dots, underscores, colons, or hyphens.")
        if job_type != "intelligence.solve":
            raise ValueError("Unsupported job type.")
        if not isinstance(payload, dict):
            raise ValueError("Job payload must be an object.")
        payload_hash = self.fingerprint({"job_type": job_type, "payload": payload})
        body = {
            "tenant_id": tenant_id,
            "requested_by": requested_by,
            "job_type": job_type,
            "status": "queued",
            "payload": payload,
            "idempotency_key": key,
            "payload_hash": payload_hash,
            "max_attempts": max_attempts,
        }
        try:
            rows = self._request("POST", "platform_jobs", params={"select": "job_id,status,created_at"}, json=body, headers={"Prefer": "return=representation"})
            if isinstance(rows, list) and rows:
                return rows[0]
            raise JobStoreUnavailable("Job queue did not confirm the inserted job.")
        except JobStoreUnavailable:
            # Distinguish a duplicate-key response from other store failures without
            # depending on a database error string or exposing it to callers.
            existing = self._request("GET", "platform_jobs", params={
                "select": "job_id,status,payload_hash,created_at",
                "tenant_id": f"eq.{tenant_id}",
                "idempotency_key": f"eq.{key}",
                "limit": "1",
            })
            if not existing:
                raise
            row = existing[0]
            if row.get("payload_hash") != payload_hash:
                raise JobConflict("Idempotency key was already used for a different job payload.")
            return {k: row[k] for k in ("job_id", "status", "created_at") if k in row}

    def get_job(self, job_id: str, *, tenant_id: str = "platform-service") -> dict[str, Any] | None:
        rows = self._request("GET", "platform_jobs", params={
            "select": "job_id,job_type,status,result_json,error_code,attempt_count,max_attempts,created_at,updated_at,completed_at",
            "job_id": f"eq.{job_id}",
            "tenant_id": f"eq.{tenant_id}",
            "limit": "1",
        })
        return rows[0] if isinstance(rows, list) and rows else None

    def reserve_user_quota(
        self, *, tenant_id: str, idempotency_key: str,
        limit: int = 20, window_seconds: int = 3600,
    ) -> bool:
        """Atomically reserve one per-user quota slot in a rolling window."""
        key = idempotency_key.strip()
        if not key or len(key) > 200 or not re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", key):
            raise ValueError("Idempotency key must use 1–200 letters, digits, dots, underscores, colons, or hyphens.")
        try:
            value = self._request("POST", "rpc/reserve_user_job_quota", json={
                "p_tenant_id": tenant_id,
                "p_idempotency_key": key,
                "p_limit": limit,
                "p_window_seconds": window_seconds,
            })
        except JobStoreUnavailable:
            # Quota checks fail closed: do not accept work if enforcement is unavailable.
            raise
        if not isinstance(value, bool):
            raise JobStoreUnavailable("User job quota service returned an invalid response.")
        return value

    def claim(self, lease_seconds: int = 120) -> dict[str, Any] | None:
        rows = self._request("POST", "rpc/claim_platform_job", json={"p_lease_seconds": lease_seconds})
        return rows[0] if isinstance(rows, list) and rows else None

    def finish(self, job_id: str, result: dict[str, Any]) -> bool:
        value = self._request("POST", "rpc/finish_platform_job", json={"p_job_id": job_id, "p_result": result})
        return value is True

    def fail(self, job_id: str, error_code: str, retry_delay_seconds: int = 30) -> bool:
        value = self._request("POST", "rpc/fail_platform_job", json={
            "p_job_id": job_id,
            "p_error_code": error_code[:80],
            "p_retry_delay_seconds": retry_delay_seconds,
        })
        return value is True
