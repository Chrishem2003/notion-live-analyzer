"""Authenticated, read-only API boundary for NEMA-AGORA case records.

Writes deliberately remain unavailable until a durable idempotency ledger and
per-actor authorization model are implemented and deployed.
"""
from __future__ import annotations

import hashlib
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


def _require_nema_read_access(
    x_api_key: Optional[str] = Header(default=None),
    x_nema_actor: Optional[str] = Header(default=None),
    x_nema_role: Optional[str] = Header(default=None),
    x_nema_signature: Optional[str] = Header(default=None),
) -> dict[str, str]:
    """Require service authentication plus a signed, server-resolved portal identity.

    The Streamlit service signs the OIDC subject and role after resolving the role
    from trusted server-side bindings. Submitters are deliberately denied this
    cross-case API because case ownership is not yet consistently modeled.
    """
    _require_nema_api_key(x_api_key=x_api_key)
    actor = x_nema_actor.strip() if isinstance(x_nema_actor, str) else ""
    role = x_nema_role.strip().lower() if isinstance(x_nema_role, str) else ""
    signature = x_nema_signature.strip() if isinstance(x_nema_signature, str) else ""
    if not actor or len(actor) > 512 or not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="A signed portal identity is required.")
    if role not in {"reviewer", "coordinator", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This role cannot access cross-case records.")
    configured = os.environ.get("PLATFORM_API_KEY", "")
    message = f"{actor}\\n{role}".encode("utf-8")
    expected = hmac.new(configured.encode("utf-8"), message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="The signed portal identity is invalid.")
    return {"actor": actor, "role": role}


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
    backend = os.environ.get("NEMA_CASE_STORAGE_BACKEND", "sqlite").strip().lower()
    if backend == "supabase_postgres":
        from nema_agora.supabase_repository import (
            NemaStorageUnavailableError,
            SupabaseReadOnlyNemaRepository,
        )

        try:
            return SupabaseReadOnlyNemaRepository()
        except NemaStorageUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="NEMA remote storage is not configured or available.",
            ) from exc
    if backend != "sqlite":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NEMA case storage backend is unsupported.",
        )
    from nema_agora.repository import NemaCaseRepository

    return NemaCaseRepository(_database_path())


def _remote_storage_error(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="NEMA case storage is temporarily unavailable.",
    )


@router.get("")
def list_cases(
    limit: int = Query(default=100, ge=1, le=1000),
    _auth: dict[str, str] = Depends(_require_nema_read_access),
):
    """List persisted case summaries; no write or enforcement operation is exposed."""
    from nema_agora.supabase_repository import NemaStorageUnavailableError

    repository = _repository()
    try:
        rows = repository.list_cases(limit=limit)
        return {
            "items": [{"record": record, "version": version} for record, version in rows],
            "count": len(rows),
            "limit": limit,
            "mode": "read_only",
        }
    except NemaStorageUnavailableError as exc:
        raise _remote_storage_error(exc) from exc
    finally:
        repository.close()


@router.get("/storage-readiness")
def storage_readiness(_auth: bool = Depends(_require_nema_read_access)):
    """Inspect configured storage without creating a database or changing records."""
    backend = os.environ.get("NEMA_CASE_STORAGE_BACKEND", "sqlite").strip().lower()
    if backend == "supabase_postgres":
        from nema_agora.supabase_repository import NemaStorageUnavailableError

        repository = _repository()
        try:
            return repository.storage_readiness()
        except NemaStorageUnavailableError as exc:
            raise _remote_storage_error(exc) from exc
        finally:
            repository.close()
    if backend != "sqlite":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NEMA case storage backend is unsupported.",
        )

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

    connection = None
    try:
        # URI read-only mode ensures diagnostics never create or migrate a database.
        connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=2.0)
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
    finally:
        if connection is not None:
            connection.close()

    schema_ready = {"nema_cases", "nema_case_audit"}.issubset(tables)
    integrity_ok = bool(integrity and integrity[0] == "ok")
    return {
        "status": "configured" if schema_ready and integrity_ok else "not_ready",
        "storage_backend": "sqlite",
        "database_file_present": True,
        "sqlite_integrity": "ok" if integrity_ok else "failed",
        "required_schema_present": schema_ready,
        "durability_flag_configured": True,
        "storage_durability_verified": False,
        "production_writes_enabled": False,
    }


@router.get("/{case_id}")
def get_case(case_id: str, _auth: bool = Depends(_require_nema_read_access)):
    """Read one persisted case and its audit history."""
    from nema_agora.supabase_repository import NemaStorageUnavailableError

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
    except NemaStorageUnavailableError as exc:
        raise _remote_storage_error(exc) from exc
    finally:
        repository.close()

@router.get("/{case_id}/review-packet")
def review_packet(case_id: str, _auth: bool = Depends(_require_nema_read_access)):
    """Build a deterministic read-only preview; this does not submit an automation job."""
    from nema_agora.supabase_repository import NemaStorageUnavailableError
    from nema_agora.workflows import build_case_review_packet

    repository = _repository()
    try:
        found = repository.get_case(case_id)
        if found is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
        record, version = found
        audit = repository.list_audit_events(case_id, limit=100)
        packet = build_case_review_packet(
            case_id,
            {"record": record, "version": version, "audit": audit, "mode": "read_only"},
        )
        packet["execution_mode"] = "preview_only"
        return packet
    except NemaStorageUnavailableError as exc:
        raise _remote_storage_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="A review packet could not be prepared from the stored case data.",
        ) from exc
    finally:
        repository.close()
