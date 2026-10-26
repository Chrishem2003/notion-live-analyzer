"""Security regression tests for the authenticated NEMA case API boundary."""
from __future__ import annotations

import hashlib
import hmac

import pytest
from fastapi import HTTPException

from nema_agora import api


def _signature(actor: str, role: str, key: str) -> str:
    message = f"{actor}\\\\n{role}".encode("utf-8")
    return hmac.new(key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def test_cross_case_api_requires_signed_server_resolved_identity(monkeypatch):
    monkeypatch.setenv("PLATFORM_API_KEY", "test-platform-key")

    with pytest.raises(HTTPException) as missing:
        api._require_nema_read_access(
            x_api_key="test-platform-key",
            x_nema_actor=None,
            x_nema_role=None,
            x_nema_signature=None,
        )
    assert missing.value.status_code == 401

    actor = "https://issuer.example|subject-123"
    with pytest.raises(HTTPException) as submitter:
        api._require_nema_read_access(
            x_api_key="test-platform-key",
            x_nema_actor=actor,
            x_nema_role="submitter",
            x_nema_signature=_signature(actor, "submitter", "test-platform-key"),
        )
    assert submitter.value.status_code == 403

    reviewer_signature = _signature(actor, "reviewer", "test-platform-key")
    identity = api._require_nema_read_access(
        x_api_key="test-platform-key",
        x_nema_actor=actor,
        x_nema_role="reviewer",
        x_nema_signature=reviewer_signature,
    )
    assert identity == {"actor": actor, "role": "reviewer"}

    with pytest.raises(HTTPException) as tampered_role:
        api._require_nema_read_access(
            x_api_key="test-platform-key",
            x_nema_actor=actor,
            x_nema_role="admin",
            x_nema_signature=reviewer_signature,
        )
    assert tampered_role.value.status_code == 401


def test_case_api_routes_require_signed_identity_dependency():
    protected_routes = {
        "/api/v1/nema/cases",
        "/api/v1/nema/cases/storage-readiness",
        "/api/v1/nema/cases/{case_id}",
        "/api/v1/nema/cases/{case_id}/review-packet",
    }
    routes = {route.path: route for route in api.router.routes}
    for path in protected_routes:
        route = routes[path]
        assert any(
            dependency.call is api._require_nema_read_access
            for dependency in route.dependant.dependencies
        ), path
