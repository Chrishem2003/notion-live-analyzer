"""Resolve authenticated OIDC claims into a least-privilege app principal.

Role assignments come from trusted server-side configuration, never user input
or unverified role claims. This module does not perform OIDC login or validate
tokens itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from nema_agora.access import ROLE_PERMISSIONS


@dataclass(frozen=True, slots=True)
class Principal:
    """Minimal application identity derived from trusted authentication claims."""

    subject_key: str
    issuer: str
    subject: str
    role: str | None
    email: str | None = None
    display_name: str | None = None

    @property
    def is_authorised(self) -> bool:
        """Whether this principal has an explicitly recognised role."""
        return self.role in ROLE_PERMISSIONS


def subject_key(issuer: str, subject: str) -> str:
    """Create a stable namespaced key; subject IDs are only unique per issuer."""
    issuer = issuer.strip()
    subject = subject.strip()
    if not issuer or not subject:
        raise ValueError("Both OIDC issuer and subject are required")
    return f"{issuer}|{subject}"


def principal_from_claims(
    *,
    is_logged_in: bool,
    claims: Mapping[str, object] | None,
    role_bindings: Mapping[str, str],
) -> Principal | None:
    """Return a principal for a logged-in user, otherwise None.

    role_bindings must come from trusted server-side configuration. Claims
    such as role, groups or is_admin are intentionally ignored to prevent
    untrusted claims from granting application permissions. An authenticated
    user without a configured role receives role=None.
    """
    if is_logged_in is not True or not isinstance(claims, Mapping):
        return None

    issuer_value = claims.get("iss")
    subject_value = claims.get("sub")
    if not isinstance(issuer_value, str) or not isinstance(subject_value, str):
        return None

    issuer = issuer_value.strip()
    subject = subject_value.strip()
    if not issuer or not subject:
        return None

    key = subject_key(issuer, subject)
    configured_role = role_bindings.get(key)
    role = (
        configured_role.strip().lower()
        if isinstance(configured_role, str)
        else None
    )
    if role not in ROLE_PERMISSIONS:
        role = None

    email_value = claims.get("email")
    name_value = claims.get("name")
    email = email_value.strip() if isinstance(email_value, str) else None
    display_name = name_value.strip() if isinstance(name_value, str) else None

    return Principal(
        subject_key=key,
        issuer=issuer,
        subject=subject,
        role=role,
        email=email or None,
        display_name=display_name or None,
    )
