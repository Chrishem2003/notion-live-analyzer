"""Fail-closed FastAPI boundary for NEMA spatial evidence.

The route is intentionally unavailable until a trusted server-side identity
resolver is wired. A non-empty Authorization header is not authentication;
actor, role, and database location must never be chosen by the HTTP caller.
"""
from __future__ import annotations

import os
from typing import Any

from nema_agora.authenticated_spatial_api import authenticated_query

POLICY_VERSION = "phase87-v2"

try:
    from fastapi import Depends, FastAPI, Header, HTTPException
    FASTAPI_AVAILABLE = True

    def require_spatial_principal(
        authorization: str | None = Header(default=None),
    ) -> dict[str, str]:
        # Fail closed until a verified OIDC/JWT adapter maps credentials to a
        # provisioned server-side subject and role. Never trust caller fields.
        raise HTTPException(
            status_code=503,
            detail="NEMA spatial API identity verification is not configured; query access is disabled.",
        )

    app = FastAPI(
        title="NEMA-AGORA Authenticated Spatial Evidence API",
        version=POLICY_VERSION,
    )

    @app.get("/api/v1/spatial-evidence/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "policy_version": POLICY_VERSION,
            "read_only": "true",
            "query_access": "disabled_until_identity_verifier_is_configured",
        }

    @app.get("/api/v1/spatial-evidence/query")
    def query(
        request_id: str,
        aoi_id: str | None = None,
        scene_id: str | None = None,
        candidate_id: str | None = None,
        review_status: str | None = None,
        observed_from: str | None = None,
        observed_to: str | None = None,
        limit: int = 100,
        principal: dict[str, str] = Depends(require_spatial_principal),
    ) -> dict[str, Any]:
        database_path = os.environ.get("NEMA_SPATIAL_EVIDENCE_DB")
        if not database_path:
            raise HTTPException(
                status_code=503,
                detail="NEMA_SPATIAL_EVIDENCE_DB is not configured on the server.",
            )
        result = authenticated_query(
            database_path=database_path,
            actor_id=principal["subject"],
            role=principal["role"],
            request_id=request_id,
            query={
                key: value
                for key, value in {
                    "aoi_id": aoi_id,
                    "scene_id": scene_id,
                    "candidate_id": candidate_id,
                    "review_status": review_status,
                    "observed_from": observed_from,
                    "observed_to": observed_to,
                }.items()
                if value is not None
            },
            limit=limit,
            token_present=True,
        )
        if result["http_status"] >= 400:
            raise HTTPException(result["http_status"], detail=result["body"])
        return result["body"]
except ImportError:
    # Keep optional-FastAPI imports safe for library-only environments.
    def require_spatial_principal(authorization: str | None = None) -> dict[str, str]:
        raise RuntimeError("FastAPI is unavailable; NEMA spatial query access is disabled.")

    app = None
    FASTAPI_AVAILABLE = False
