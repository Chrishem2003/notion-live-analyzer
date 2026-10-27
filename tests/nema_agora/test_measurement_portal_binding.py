from __future__ import annotations

import hashlib
import hmac

import pytest

from nema_agora.identity import Principal
from nema_agora.measurement_portal_binding import (
    MeasurementPortalBindingError,
    build_measurement_identity_headers,
)


def _principal(role="submitter"):
    return Principal(
        subject_key="https://issuer.example|subject-123",
        issuer="https://issuer.example",
        subject="subject-123",
        role=role,
    )


def _secrets():
    return {
        "PLATFORM_API_KEY": "platform-key-for-tests",
        "NEMA_PORTAL_SIGNING_SECRET": "distinct-signing-secret-with-at-least-32-chars",
    }


def test_identity_headers_sign_only_server_resolved_principal():
    headers = build_measurement_identity_headers(principal=_principal(), secrets=_secrets())
    assert headers["X-Nema-Actor"] == "https://issuer.example|subject-123"
    assert headers["X-Nema-Role"] == "submitter"
    expected = hmac.new(
        _secrets()["NEMA_PORTAL_SIGNING_SECRET"].encode(),
        b"https://issuer.example|subject-123\nsubmitter",
        hashlib.sha256,
    ).hexdigest()
    assert headers["X-Nema-Signature"] == expected
    assert headers["X-API-Key"] == "platform-key-for-tests"


def test_identity_headers_reject_unprovisioned_and_read_only_roles():
    unprovisioned = Principal(
        subject_key="https://issuer.example|subject-123",
        issuer="https://issuer.example",
        subject="subject-123",
        role=None,
    )
    with pytest.raises(MeasurementPortalBindingError):
        build_measurement_identity_headers(principal=unprovisioned, secrets=_secrets())
    with pytest.raises(MeasurementPortalBindingError):
        build_measurement_identity_headers(principal=_principal("reviewer"), secrets=_secrets())


def test_identity_headers_reject_missing_or_reused_secrets():
    with pytest.raises(MeasurementPortalBindingError):
        build_measurement_identity_headers(principal=_principal(), secrets={})
    bad = _secrets()
    bad["NEMA_PORTAL_SIGNING_SECRET"] = bad["PLATFORM_API_KEY"]
    with pytest.raises(MeasurementPortalBindingError):
        build_measurement_identity_headers(principal=_principal(), secrets=bad)


def test_identity_headers_reject_actor_newline_injection():
    principal = Principal(
        subject_key="https://issuer.example|subject-123\nadmin",
        issuer="https://issuer.example",
        subject="subject-123",
        role="submitter",
    )
    with pytest.raises(MeasurementPortalBindingError):
        build_measurement_identity_headers(principal=principal, secrets=_secrets())
