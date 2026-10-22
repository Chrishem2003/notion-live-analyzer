"""Authenticated, read-only API boundary for NEMA-AGORA case records.

Writes deliberately remain unavailable here until a durable idempotency ledger and
per-actor authorization model are implemented and deployed. The repository itself
does not authenticate callers or prove that a host path is durable.
"""
from __future__ import annotations

import hmac
import os
import sqlite3
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


@router.get("/storage-readiness")
def storage_readiness(_auth: bool = Depends(_require_nema_api_key)):
    """Inspect configured storage without creating a database or changing records.

    A healthy SQLite file and an explicit durability flag are necessary but do not
    independently prove that the hosting provider preserves the underlying disk.
    """
    path = _database_path()
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "reason": "database_file_missing",
                "database_file_present": False,
                "storage_durability_verified": False,
            },
        )

    try:
        # URI read-only mode ensures diagnostics never create or migrate a database.
        with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=2.0) as connection:
            integrity = connection.execute("PRAGMA quick_check").fetchone()
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
    except (OSError, sqlite3.Error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "reason": "database_unreadable_or_invalid",
                "database_file_present": True,
                "storage_durability_verified": False,
            },
        )

    schema_ready = {"nema_cases", "nema_case_audit"}.issubset(tables)
    integrity_ok = bool(integrity and integrity[0] == "ok")
    return {
        "status": "configured" if schema_ready and integrity_ok else "not_ready",
        "database_file_present": True,
        "sqlite_integrity": "ok" if integrity_ok else "failed",
        "required_schema_present": schema_ready,
        "durability_flag_configured": True,
        # This requires independent confirmation of the hosting disk/mount.
        "storage_durability_verified": False,
        "production_writes_enabled": False,
    }


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
