"""Audited, side-effect-free case transition service for NEMA-AGORA.

This module validates and prepares a proposed record update plus an audit event.
It deliberately does not persist data, authenticate actors, or call external systems;
those responsibilities belong to a future authenticated persistence boundary.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from nema_agora.core import STATUSES, validate_status_transition


def apply_case_transition(
    record: Mapping[str, Any],
    *,
    new_status: str,
    actor: str,
    changed_at: str,
    reason: str = "",
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Return a copied record and audit event, or raise ValueError.

    The original mapping is never mutated. Timestamps must be ISO-8601 and
    timezone-aware. Repeating a status is a no-op and emits no audit event.
    This is not an authorization check and must not be exposed as a write API
    without authenticated identity, durable storage, and concurrency control.
    """
    if not isinstance(record, Mapping):
        raise ValueError("record must be a mapping")
    case_id = record.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("A case ID is required.")
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError("An authenticated actor identifier is required.")
    if len(actor.strip()) > 120:
        raise ValueError("Actor identifier must be 120 characters or fewer.")
    if not isinstance(reason, str) or len(reason) > 500:
        raise ValueError("Reason must be text of 500 characters or fewer.")
    if not isinstance(changed_at, str) or not changed_at.strip():
        raise ValueError("A timezone-aware ISO-8601 timestamp is required.")
    try:
        parsed_time = datetime.fromisoformat(changed_at.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Timestamp must be valid ISO-8601.") from exc
    if parsed_time.tzinfo is None or parsed_time.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone offset.")

    current_status = record.get("status")
    errors = validate_status_transition(
        current_status if isinstance(current_status, str) else "",
        new_status,
        reason=reason,
    )
    if errors:
        raise ValueError(" ".join(errors))

    updated = dict(record)
    if current_status == new_status:
        return updated, None

    updated["status"] = new_status
    event = {
        "event_type": "case_status_transition",
        "case_id": case_id.strip(),
        "from_status": current_status,
        "to_status": new_status,
        "actor": actor.strip(),
        "changed_at": parsed_time.isoformat(),
        "reason": reason.strip(),
    }
    return updated, event
