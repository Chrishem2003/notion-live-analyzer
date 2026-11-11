"""Opt-in per-user durable-job API.

Unlike the legacy service-key API, this router derives the owner from a token
verified by Supabase Auth. It is not mounted unless USER_JOB_API_ENABLED=true.
The backend service-role key is used only inside the server-side repository.
"""
from __future__ import annotations

import os
from typing import Optional
from uuid import UUID

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, validator

from platform_jobs.repository import JobConflict, JobStoreUnavailable, SupabaseJobRepository

router = APIRouter(prefix="/api/v1/user-jobs", tags=["user-durable-jobs"])


def _enabled() -> bool:
    return os.environ.get("USER_JOB_API_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def _quota_limit() -> int:
    raw = os.environ.get("USER_JOB_QUOTA_PER_HOUR", "20").strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise JobStoreUnavailable("User job quota configuration is invalid.") from exc
    if value < 1 or value > 1000:
        raise JobStoreUnavailable("User job quota configuration is out of range.")
    return value


def _verified_user(authorization: Optional[str] = Header(default=None)) -> dict[str, str]:
    if not _enabled():
        raise HTTPException(status_code=503, detail="Per-user job API is disabled.")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
    token = authorization[7:].strip()
    base_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    public_key = (os.environ.get("SUPABASE_PUBLISHABLE_KEY") or os.environ.get("SUPABASE_ANON_KEY") or "").strip()
    if not base_url.startswith("https://") or not public_key:
        raise HTTPException(status_code=503, detail="User authentication is not configured.")
    try:
        response = requests.get(
            f"{base_url}/auth/v1/user",
            headers={"apikey": public_key, "Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if response.status_code == 429 or response.status_code >= 500:
            raise HTTPException(status_code=503, detail="Authentication verification is temporarily unavailable.")
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid or expired bearer token.")
        payload = response.json()
        user_id = str(UUID(str(payload.get("id", ""))))
        email = payload.get("email")
        return {"id": user_id, "email": email if isinstance(email, str) else ""}
    except HTTPException:
        raise
    except requests.RequestException as exc:
        # A network/provider outage is not proof that the user's token is invalid.
        # Return 503 so clients can retry instead of forcing a misleading re-login.
        raise HTTPException(status_code=503, detail="Authentication verification is temporarily unavailable.") from exc
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=401, detail="Unable to verify bearer token.") from exc


class UserJobCreateRequest(BaseModel):
    job_type: str = Field(default="intelligence.solve", min_length=1, max_length=80)
    prompt: str = Field(..., min_length=1, max_length=12000)
    provider: Optional[str] = Field(default=None, max_length=40)
    model: Optional[str] = Field(default=None, max_length=200)
    strategy: str = Field(default="direct", min_length=1, max_length=80)
    max_attempts: int = Field(default=3, ge=1, le=5)

    class Config:
        # Reject attempted ownership/role injection rather than silently ignoring it.
        extra = "forbid"

    @validator("prompt")
    def prompt_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Prompt cannot be blank.")
        return value

    @validator("provider", "model", "strategy")
    def optional_routing_values_must_not_be_blank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Provider, model, and strategy values cannot be blank.")
        return value


@router.post("", status_code=202)
def create_user_job(
    payload: UserJobCreateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=200),
    user: dict[str, str] = Depends(_verified_user),
):
    if payload.job_type != "intelligence.solve":
        raise HTTPException(status_code=422, detail="Unsupported job type.")
    repo = None
    try:
        repo = SupabaseJobRepository()
        allowed = repo.reserve_user_quota(
            tenant_id=user["id"], idempotency_key=idempotency_key,
            limit=_quota_limit(),
            window_seconds=3600,
        )
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="User job quota reached. Try again after the rolling quota window resets.",
                headers={"Retry-After": "3600"},
            )
        row = repo.enqueue(
            idempotency_key=idempotency_key,
            job_type=payload.job_type,
            payload={"prompt": payload.prompt.strip(), "provider": payload.provider, "model": payload.model, "strategy": payload.strategy},
            max_attempts=payload.max_attempts,
            tenant_id=user["id"],
            requested_by=user["id"],
        )
        return {"job_id": row.get("job_id"), "status": row.get("status", "queued"), "created_at": row.get("created_at"), "mode": "user_scoped"}
    except HTTPException:
        raise
    except JobConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (JobStoreUnavailable, ValueError) as exc:
        raise HTTPException(status_code=503 if isinstance(exc, JobStoreUnavailable) else 422, detail=str(exc)) from exc
    finally:
        if repo:
            repo.close()


@router.delete("/{job_id}")
def cancel_user_job(job_id: str, user: dict[str, str] = Depends(_verified_user)):
    """Cancel only the authenticated user's queued/running job."""
    try:
        parsed_id = str(UUID(job_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail="job_id must be a UUID.") from exc
    repo = None
    try:
        repo = SupabaseJobRepository()
        outcome = repo.cancel_user_job(job_id=parsed_id, tenant_id=user["id"])
        if outcome == "not_found":
            raise HTTPException(status_code=404, detail="Job not found.")
        if outcome == "not_cancellable":
            raise HTTPException(status_code=409, detail="Job is no longer cancellable.")
        return {"job_id": parsed_id, "status": "cancelled"}
    except HTTPException:
        raise
    except JobStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="Durable job storage is temporarily unavailable.") from exc
    finally:
        if repo:
            repo.close()


@router.get("/{job_id}")
def get_user_job(job_id: str, user: dict[str, str] = Depends(_verified_user)):
    try:
        parsed_id = str(UUID(job_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail="job_id must be a UUID.") from exc
    repo = None
    try:
        repo = SupabaseJobRepository()
        row = repo.get_job(parsed_id, tenant_id=user["id"])
        if row is None:
            # Same response for nonexistent and another user's job to prevent enumeration.
            raise HTTPException(status_code=404, detail="Job not found.")
        return row
    except JobStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="Durable job storage is temporarily unavailable.") from exc
    finally:
        if repo:
            repo.close()
