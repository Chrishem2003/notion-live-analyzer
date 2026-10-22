"""Fail-closed standalone spatial-evidence query application.

This legacy app used to accept a caller-supplied SQLite path and queried it
without authentication. It now shares the same disabled-by-default trusted
identity boundary as the authenticated route app.
"""
from __future__ import annotations

import os
from typing import Any

from nema_agora.spatial_evidence_api_hardening import query_persistent_evidence
from nema_agora.fastapi_authenticated_routes import require_spatial_principal

POLICY_VERSION = "phase84-v2"

try:
    from fastapi import Depends, FastAPI, HTTPException
    FASTAPI_AVAILABLE = True

    app = FastAPI(title="NEMA-AGORA Spatial Evidence API", version=POLICY_VERSION)

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
        # The principal is deliberately required even though the current
        # default dependency rejects all queries. Storage paths stay server-side.
        _ = principal
        database_path = os.environ.get("NEMA_SPATIAL_EVIDENCE_DB")
        if not database_path:
            raise HTTPException(
                status_code=503,
                detail="NEMA_SPATIAL_EVIDENCE_DB is not configured on the server.",
            )
        result = query_persistent_evidence(
            database_path=database_path,
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
        )
        if result["http_status"] >= 400:
            raise HTTPException(result["http_status"], detail=result["body"])
        return result["body"]
except ImportError:
    app = None
    FASTAPI_AVAILABLE = False


def app_contract() -> dict[str, Any]:
    return {
        "application": "NEMA-AGORA Spatial Evidence API",
        "policy_version": POLICY_VERSION,
        "fastapi_available": FASTAPI_AVAILABLE,
        "read_only": True,
        "authorization_required": True,
        "identity_verifier_configured": False,
        "query_enabled_by_default": False,
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
    }
