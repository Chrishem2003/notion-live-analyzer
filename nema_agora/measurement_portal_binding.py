"""Server-side signing adapter for future NEMA measurement submissions.

Only accepts a Principal resolved by nema_agora.auth from authenticated OIDC
claims and server-side role bindings. It never accepts identity or role strings
from a request payload. This module prepares headers only; it does not send HTTP.
"""
from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from typing import Any

from nema_agora.identity import Principal


_ALLOWED_ROLES = {"submitter", "coordinator", "admin"}


class MeasurementPortalBindingError(ValueError):
    """Raised when trusted portal identity or signing configuration is invalid."""


def build_measurement_identity_headers(
    *, principal: Principal | None, secrets: Mapping[str, Any]
) -> dict[str, str]:
    """Build API identity headers from a verified, server-bound Principal.

    `principal` must come from `resolve_principal(st)`; do not build it from
    request JSON or caller-supplied role fields. The API key and signing secret
    are distinct server-side configuration values.
    """
    if not isinstance(principal, Principal) or not principal.is_authorised:
        raise MeasurementPortalBindingError("An authorised portal principal is required.")
    role = principal.role
    if role not in _ALLOWED_ROLES:
        raise MeasurementPortalBindingError("This portal role cannot submit measurements.")

    platform_key = secrets.get("PLATFORM_API_KEY")
    signing_secret = secrets.get("NEMA_PORTAL_SIGNING_SECRET")
    if not isinstance(platform_key, str) or not platform_key.strip():
        raise MeasurementPortalBindingError("Platform API key is not configured.")
    if not isinstance(signing_secret, str) or len(signing_secret.strip()) < 32:
        raise MeasurementPortalBindingError("Portal signing secret must contain at least 32 characters.")
    if hmac.compare_digest(signing_secret.strip(), platform_key.strip()):
        raise MeasurementPortalBindingError("Portal signing secret must differ from the platform API key.")

    actor = principal.subject_key.strip()
    if not actor or len(actor) > 512 or "\n" in actor or "\r" in actor:
        raise MeasurementPortalBindingError("Portal principal has an invalid subject key.")
    message = f"{actor}\n{role}".encode("utf-8")
    signature = hmac.new(signing_secret.strip().encode("utf-8"), message, hashlib.sha256).hexdigest()
    return {
        "X-API-Key": platform_key.strip(),
        "X-Nema-Actor": actor,
        "X-Nema-Role": role,
        "X-Nema-Signature": signature,
    }
