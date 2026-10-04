"""Role-based permission policy for NEMA-AGORA.

This module evaluates permissions for an identity that has already been
authenticated by a trusted identity provider. It does not authenticate users,
create sessions, or establish that a supplied actor ID is genuine.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Final

PERMISSIONS: Final = frozenset(
    {
        "observation:create",
        "observation:read_own",
        "observation:read_all",
        "observation:review",
        "case:export",
        "metrics:read",
        "intelligence:use",
        "intelligence:feedback",
        "intelligence:shadow",
        "intelligence:lab",
        "intelligence:comparison",
        "intelligence:admit_model",
        "intelligence:controlled_shadow",
        "intelligence:monitor",
        "intelligence:provenance",
        "intelligence:field_eval",
        "intelligence:impact",
        "intelligence:review_shadow",
        "intelligence:govern_shadow",
        "annotation:create",
        "annotation:read_own",
        "annotation:read_all",
        "annotation:adjudicate",
        "audit:read",
        "user:manage",
    }
)

_ROLE_PERMISSIONS = {
    "submitter": frozenset({"observation:create", "observation:read_own"}),
    "reviewer": frozenset(
        {"observation:read_all", "observation:review", "metrics:read", "intelligence:use", "intelligence:feedback", "intelligence:shadow", "intelligence:lab", "intelligence:comparison", "intelligence:controlled_shadow", "intelligence:monitor", "annotation:create", "annotation:read_own", "intelligence:review_shadow"}
    ),
    "coordinator": frozenset(
        {
            "observation:read_all",
            "observation:review",
            "case:export",
            "metrics:read",
            "audit:read",
            "intelligence:use",
            "intelligence:feedback",
            "intelligence:shadow",
            "intelligence:lab",
            "intelligence:comparison",
            "intelligence:admit_model",
            "intelligence:controlled_shadow",
            "intelligence:monitor",
            "intelligence:provenance",
            "intelligence:field_eval",
            "annotation:create",
            "annotation:read_own",
            "annotation:read_all",
            "annotation:adjudicate",
            "intelligence:review_shadow",
            "intelligence:govern_shadow",
        }
    ),
    "admin": PERMISSIONS,
}
ROLE_PERMISSIONS: Final = MappingProxyType(_ROLE_PERMISSIONS)


def has_permission(role: str | None, permission: str) -> bool:
    """Return False for unknown roles or permissions (deny by default)."""
    if not isinstance(role, str) or not isinstance(permission, str):
        return False
    if permission not in PERMISSIONS:
        return False
    return permission in ROLE_PERMISSIONS.get(role.strip().lower(), frozenset())


def require_permission(role: str | None, permission: str) -> None:
    """Raise PermissionError unless the role is explicitly allowed."""
    if not has_permission(role, permission):
        raise PermissionError(f"Role is not permitted to perform: {permission}")


def can_read_observation(
    role: str | None, actor_id: str | None, owner_id: str | None
) -> bool:
    """Check record-read policy after identity has been authenticated.

    Submitters may read only records whose owner ID matches their trusted actor
    ID. Other access requires the explicit read-all permission. Blank or
    missing identifiers are never treated as a match.
    """
    if has_permission(role, "observation:read_all"):
        return True
    if not has_permission(role, "observation:read_own"):
        return False
    return (
        isinstance(actor_id, str)
        and isinstance(owner_id, str)
        and bool(actor_id.strip())
        and bool(owner_id.strip())
        and actor_id == owner_id
    )
