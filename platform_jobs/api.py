"""Authenticated service-to-service API for submitting and polling durable jobs.

This endpoint intentionally uses the existing platform API key and a single
service-owned tenant. It is not end-user authentication. Keep it server-side;
per-user JWT identity and tenant isolation must be added before browser exposure.
"""
from __future__ import annotations

import hmac
import os
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, validator

from platform_jobs.repository import JobConflict, JobStoreUnavailable, SupabaseJobRepository

router = APIRouter(prefix="/api/v1/jobs", tags=["durable-jobs"])


def _require_service_key(x_api_key: Optional[str] = Header(default=None)) -> bool:
    configured = os.environ.get("PLATFORM_API_KEY", "").strip()
    if not configured:
        raise HTTPException(status_code=503, detail="Job API is not configured.")
    if not x_api_key or not hmac.compare_digest(x_api_key, configured):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key.")
    return True


class JobCreateRequest(BaseModel):
    job_type: str = Field(default="intelligence.solve", min_length=1, max_length=80)
    prompt: str = Field(..., min_length=1, max_length=12000)
    provider: Optional[str] = Field(default=None, max_length=40)
    model: Optional[str] = Field(default=None, max_length=200)
    strategy: str = Field(default="direct", min_length=1, max_length=80)
    max_attempts: int = Field(default=3, ge=1, le=5)

    @validator("prompt")
    def prompt_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Prompt cannot be blank.")
        return value


@router.post("", status_code=202, dependencies=[Depends(_require_service_key)])
def create_job(payload: JobCreateRequest, idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=200)):
    if payload.job_type != "intelligence.solve":
        raise HTTPException(status_code=422, detail="Unsupported job type.")
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Prompt cannot be blank.")
    repo = None
    try:
        repo = SupabaseJobRepository()
        row = repo.enqueue(
            idempotency_key=idempotency_key,
            job_type=payload.job_type,
            payload={"prompt": prompt, "provider": payload.provider, "model": payload.model, "strategy": payload.strategy},
            max_attempts=payload.max_attempts,
        )
        return {"job_id": row.get("job_id"), "status": row.get("status", "queued"), "created_at": row.get("created_at"), "mode": "durable_queue"}
    except JobConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (JobStoreUnavailable, ValueError) as exc:
        raise HTTPException(status_code=503 if isinstance(exc, JobStoreUnavailable) else 422, detail=str(exc)) from exc
    finally:
        if repo:
            repo.close()


@router.get("/{job_id}", dependencies=[Depends(_require_service_key)])
def get_job(job_id: str):
    try:
        parsed_id = str(UUID(job_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail="job_id must be a UUID.") from exc
    repo = None
    try:
        repo = SupabaseJobRepository()
        row = repo.get_job(parsed_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return row
    except JobStoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="Durable job storage is temporarily unavailable.") from exc
    finally:
        if repo:
            repo.close()
