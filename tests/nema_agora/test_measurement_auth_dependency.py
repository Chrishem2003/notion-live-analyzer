from __future__ import annotations

import hashlib
import hmac

import pytest
from fastapi import HTTPException

from nema_agora.api import _require_measurement_submission_access


def _signature(secret: str, actor: str, role: str) -> str:
    message = f"{actor}\n{role}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _call(*, api_key: str | None, actor: str | None, role: str | None, signature: str | None):
    return _require_measurement_submission_access(
        x_api_key=api_key,
        x_nema_actor=actor,
        x_nema_role=role,
        x_nema_signature=signature,
    )


def _configure(monkeypatch, *, api_key="test-platform-key", secret="s" * 48):
    monkeypatch.setenv("PLATFORM_API_KEY", api_key)
    monkeypatch.setenv("NEMA_PORTAL_SIGNING_SECRET", secret)
    return api_key, secret


def test_measurement_auth_accepts_only_valid_signed_server_identity(monkeypatch):
    api_key, secret = _configure(monkeypatch)
    signature = _signature(secret, "oidc|subject-42", "submitter")

    principal = _call(
        api_key=api_key,
        actor="oidc|subject-42",
        role="submitter",
        signature=signature,
    )

    assert principal == {
        "authenticated": True,
        "subject": "oidc|subject-42",
        "role": "submitter",
    }


@pytest.mark.parametrize("role", ["viewer", "reviewer", "owner", ""])
def test_measurement_auth_rejects_roles_outside_submission_allowlist(monkeypatch, role):
    api_key, secret = _configure(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        _call(
            api_key=api_key,
            actor="oidc|subject-42",
            role=role,
            signature=_signature(secret, "oidc|subject-42", role),
        )
    assert exc.value.status_code == 403


@pytest.mark.parametrize("actor", ["oidc|subject-42\nadmin", "oidc|subject-42\radmin"])
def test_measurement_auth_rejects_newline_in_actor_identity(monkeypatch, actor):
    api_key, secret = _configure(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        _call(
            api_key=api_key,
            actor=actor,
            role="submitter",
            signature=_signature(secret, actor, "submitter"),
        )
    assert exc.value.status_code == 401


def test_measurement_auth_rejects_tampered_actor_role_or_signature(monkeypatch):
    api_key, secret = _configure(monkeypatch)
    valid = _signature(secret, "oidc|subject-42", "submitter")

    with pytest.raises(HTTPException) as actor_error:
        _call(api_key=api_key, actor="oidc|other", role="submitter", signature=valid)
    assert actor_error.value.status_code == 401

    with pytest.raises(HTTPException) as role_error:
        _call(api_key=api_key, actor="oidc|subject-42", role="admin", signature=valid)
    assert role_error.value.status_code == 401


def test_measurement_auth_fails_closed_when_platform_key_is_missing(monkeypatch):
    monkeypatch.delenv("PLATFORM_API_KEY", raising=False)
    monkeypatch.setenv("NEMA_PORTAL_SIGNING_SECRET", "s" * 48)

    with pytest.raises(HTTPException) as exc:
        _call(
            api_key="anything",
            actor="oidc|subject-42",
            role="submitter",
            signature="0" * 64,
        )
    assert exc.value.status_code == 503


def test_measurement_auth_rejects_missing_or_reused_signing_secret(monkeypatch):
    api_key = "test-platform-key"
    monkeypatch.setenv("PLATFORM_API_KEY", api_key)
    monkeypatch.setenv("NEMA_PORTAL_SIGNING_SECRET", api_key)
    with pytest.raises(HTTPException) as reused:
        _call(api_key=api_key, actor="oidc|subject-42", role="submitter", signature="0" * 64)
    assert reused.value.status_code == 503

    monkeypatch.setenv("NEMA_PORTAL_SIGNING_SECRET", "short")
    with pytest.raises(HTTPException) as short:
        _call(api_key=api_key, actor="oidc|subject-42", role="submitter", signature="0" * 64)
    assert short.value.status_code == 503
