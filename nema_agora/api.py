"""Authenticated, read-only API boundary for NEMA-AGORA case records.

Writes deliberately remain unavailable here until a durable idempotency ledger and
per-actor authorization model are implemented and deployed. The repository itself
does not authenticate callers or prove that a host path is durable.
"""
from __future__ import annotations

import hmac
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

router = APIRouter(prefix="/api/v1/nema/cases", tags=["NEMA-AGORA"])


def _require_nema_api_key(x_api_key: Optional[str] = Header(default=None)) -> bool:
    """Authenticate service-to-service calls without trusting caller-supplied actor names."""
    configured = os.environ.get("PLATFORM_API_KEY", "")
    if not configured.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NEMA case API is unavailable because platform authentication is not configured.",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, configured):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key.")
    return True


def _database_path() -> Path:
    raw = os.environ.get("NEMA_CASE_DATABASE_PATH", "").strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NEMA case storage is not configured.",
        )
    path = Path(raw).expanduser().resolve()
    ephemeral_roots = (Path("/tmp"), Path("/var/tmp"))
    if any(path == root or root in path.parents for root in ephemeral_roots):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NEMA case storage points to an ephemeral path; durable storage is required.",
        )
    if os.environ.get("NEMA_CASE_STORAGE_DURABLE", "").strip().lower() != "true":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NEMA case storage durability has not been explicitly configured.",
        )
    return path


def _repository():
    from nema_agora.repository import NemaCaseRepository

    return NemaCaseRepository(_database_path())


@router.get("")
def list_cases(
    limit: int = Query(default=100, ge=1, le=1000),
    _auth: bool = Depends(_require_nema_api_key),
):
    """List persisted case summaries; no write or enforcement operation is exposed."""
    repository = _repository()
    try:
        rows = repository.list_cases(limit=limit)
        return {
            "items": [{"record": record, "version": version} for record, version in rows],
            "count": len(rows),
            "limit": limit,
            "mode": "read_only",
        }
    finally:
        repository.close()


@router.get("/{case_id}")
def get_case(case_id: str, _auth: bool = Depends(_require_nema_api_key)):
    """Read one persisted case and its audit history."""
    repository = _repository()
    try:
        found = repository.get_case(case_id)
        if found is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
        record, version = found
        return {
            "record": record,
            "version": version,
            "audit": repository.list_audit_events(case_id, limit=100),
            "mode": "read_only",
        }
    finally:
        repository.close()
