"""Read-only Supabase PostgREST adapter for NEMA case storage.

This adapter deliberately exposes reads only. It requires a server-side service
credential, uses bounded HTTP timeouts, and never includes credentials in errors.
Writes must be implemented through audited transactional database functions before
this backend can be used for production changes.
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import requests


class NemaStorageUnavailableError(RuntimeError):
    """Raised when remote NEMA storage is not configured or cannot be read."""


class SupabaseReadOnlyNemaRepository:
    """Minimal read-only repository contract backed by Supabase PostgREST."""

    def __init__(self, *, session: Any | None = None, timeout: float = 5.0) -> None:
        base_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
        service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise NemaStorageUnavailableError("NEMA remote storage URL is not configured with HTTPS.")
        if not service_key:
            raise NemaStorageUnavailableError("NEMA remote storage credentials are not configured.")
        self._base_url = base_url
        self._timeout = timeout
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Accept": "application/json",
            }
        )

    def close(self) -> None:
        close = getattr(self._session, "close", None)
        if callable(close):
            close()

    def _get(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        try:
            response = self._session.get(
                f"{self._base_url}/rest/v1/{table}",
                params=params,
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError, TypeError) as exc:
            raise NemaStorageUnavailableError("NEMA remote storage read failed.") from exc
        if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
            raise NemaStorageUnavailableError("NEMA remote storage returned an invalid response.")
        return payload

    def list_cases(self, *, limit: int = 100) -> list[tuple[dict[str, Any], int]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("Limit must be an integer between 1 and 1000.")
        rows = self._get(
            "nema_cases",
            {
                "select": "record_json,version",
                "order": "created_at.desc,case_id.asc",
                "limit": str(limit),
            },
        )
        result: list[tuple[dict[str, Any], int]] = []
        for row in rows:
            record, version = row.get("record_json"), row.get("version")
            if not isinstance(record, dict) or isinstance(version, bool) or not isinstance(version, int):
                raise NemaStorageUnavailableError("NEMA case storage returned an invalid record.")
            result.append((record, version))
        return result

    def get_case(self, case_id: str) -> tuple[dict[str, Any], int] | None:
        if not isinstance(case_id, str) or not case_id.strip() or len(case_id) > 80:
            return None
        rows = self._get(
            "nema_cases",
            {
                "select": "record_json,version",
                "case_id": f"eq.{case_id}",
                "limit": "1",
            },
        )
        if not rows:
            return None
        record, version = rows[0].get("record_json"), rows[0].get("version")
        if not isinstance(record, dict) or isinstance(version, bool) or not isinstance(version, int):
            raise NemaStorageUnavailableError("NEMA case storage returned an invalid record.")
        return record, version

    def list_audit_events(self, case_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("Limit must be an integer between 1 and 1000.")
        rows = self._get(
            "nema_case_audit",
            {
                "select": "event_json",
                "case_id": f"eq.{case_id}",
                "order": "created_at.asc,audit_id.asc",
                "limit": str(limit),
            },
        )
        events = [row.get("event_json") for row in rows]
        if any(not isinstance(event, dict) for event in events):
            raise NemaStorageUnavailableError("NEMA audit storage returned an invalid event.")
        return events

    def storage_readiness(self) -> dict[str, Any]:
        """Verify table reachability/schema only; do not claim backup or disk durability."""
        cases = self._get(
            "nema_cases",
            {"select": "case_id,record_json,version,created_at,updated_at", "limit": "0"},
        )
        audits = self._get(
            "nema_case_audit",
            {"select": "audit_id,case_id,event_type,event_json,created_at", "limit": "0"},
        )
        return {
            "status": "configured",
            "storage_backend": "supabase_postgres",
            "database_reachable": True,
            "required_schema_present": True,
            "storage_durability_verified": False,
            "production_writes_enabled": False,
        }
