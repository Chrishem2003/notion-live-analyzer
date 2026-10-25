"""Authenticated service API for the existing Sovereign Intelligence engine.

This router is intended for trusted service-to-service callers. It uses the
platform API key, never returns provider credentials, and keeps the existing
Streamlit interface and orchestration implementation intact.
"""
from __future__ import annotations

import hmac
import os
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/intelligence", tags=["sovereign-intelligence"])


def require_intelligence_api_key(
    x_api_key: Optional[str] = Header(default=None),
) -> bool:
    configured_key = os.environ.get("PLATFORM_API_KEY", "").strip()
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intelligence API is disabled until PLATFORM_API_KEY is configured.",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header.",
        )
    return True


class IntelligenceSolveRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=12000)
    provider: Optional[str] = Field(default=None, max_length=40)
    model: Optional[str] = Field(default=None, max_length=200)
    strategy: str = Field(default="direct", min_length=1, max_length=80)


@lru_cache(maxsize=1)
def _get_brain():
    # Lazy import keeps the general platform API bootable even if an optional
    # AI-provider dependency is unavailable. The route reports a safe 503.
    from sovereign_intelligence.orchestrator import SovereignBrain

    return SovereignBrain()


@router.get("/providers", dependencies=[Depends(require_intelligence_api_key)])
def list_intelligence_providers():
    """Return configured provider names only; never expose keys or raw env."""
    try:
        brain = _get_brain()
        return {
            "providers": brain.providers.configured_names(),
            "default_provider": brain.config.default_provider,
            "fallback_provider": brain.config.fallback_provider,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Sovereign Intelligence is not ready.",
                "reason": type(exc).__name__,
            },
        ) from exc


@router.post("/solve", dependencies=[Depends(require_intelligence_api_key)])
def solve_intelligence_problem(payload: IntelligenceSolveRequest):
    """Run one governed intelligence request through the existing brain."""
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="prompt cannot be blank.")

    try:
        brain = _get_brain()
        result = brain.solve_governed(
            prompt=prompt,
            provider=payload.provider,
            model=payload.model,
            strategy=payload.strategy,
        )
        verification = getattr(result, "verification", None)
        return {
            "status": "completed",
            "answer": result.answer,
            "provider": result.provider,
            "model": result.model,
            "sources": result.sources,
            "verification": (
                {
                    "passed": getattr(verification, "passed", None),
                    "confidence": getattr(verification, "confidence", None),
                }
                if verification is not None
                else None
            ),
            "governance": {
                "accepted": getattr(getattr(result, "assessment", None), "accepted", None),
                "action": getattr(
                    getattr(getattr(result, "control", None), "action", None),
                    "value",
                    None,
                ),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        # Do not leak prompts, credentials, provider responses, or stack traces.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Sovereign Intelligence could not complete this request.",
                "reason": type(exc).__name__,
            },
        ) from exc
