"""Streamlit OIDC identity adapter for NEMA-AGORA.

Streamlit performs OIDC authentication; this module maps the authenticated
issuer+subject pair to a server-side role binding. Role claims from the
identity provider are never trusted for authorization.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nema_agora.identity import Principal, principal_from_claims


def user_claims(user: Any) -> Mapping[str, object]:
    """Return a defensive claims mapping from Streamlit st.user."""
    if user is None:
        return {}
    try:
        claims = user.to_dict()
    except AttributeError:
        try:
            claims = dict(user)
        except (TypeError, ValueError):
            return {}
    return claims if isinstance(claims, Mapping) else {}


def is_logged_in(user: Any) -> bool:
    """Return authentication state without assuming auth is configured."""
    return bool(getattr(user, "is_logged_in", False))


def role_bindings_from_secrets(secrets: Mapping[str, object]) -> dict[str, str]:
    """Extract trusted issuer|subject -> role bindings from Streamlit secrets."""
    section = secrets.get("nema_agora", {})
    if not isinstance(section, Mapping):
        return {}
    bindings = section.get("role_bindings", {})
    if not isinstance(bindings, Mapping):
        return {}
    result: dict[str, str] = {}
    for key, role in bindings.items():
        if isinstance(key, str) and isinstance(role, str) and key.strip() and role.strip():
            result[key.strip()] = role.strip().lower()
    return result


def principal_from_streamlit_user(user: Any, secrets: Mapping[str, object]) -> Principal | None:
    """Resolve the current Streamlit user into a least-privilege principal."""
    return principal_from_claims(
        is_logged_in=is_logged_in(user),
        claims=user_claims(user),
        role_bindings=role_bindings_from_secrets(secrets),
    )



def resolve_principal(streamlit_module: Any) -> Principal | None:
    """Resolve the current Streamlit session without trusting client role claims.

    Missing user/secrets objects, malformed configuration, and unexpected adapter
    errors fail closed to no principal so protected pages can stop safely.
    """
    try:
        user = getattr(streamlit_module, "user", None)
        secrets = getattr(streamlit_module, "secrets", {})
        if not isinstance(secrets, Mapping):
            return None
        return principal_from_streamlit_user(user, secrets)
    except (AttributeError, TypeError, ValueError, KeyError):
        return None
