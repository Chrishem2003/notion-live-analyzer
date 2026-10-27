"""Small, testable status-transition rules for the NEMA-AGORA pilot.

This is a workflow safeguard, not an authenticated audit system. Actor identity,
durable logging, and role-based permissions must be added before multi-user use.
"""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from nema_agora.core import STATUSES, validate_status_transition

ALLOWED_TRANSITIONS = {
    "Received": {"Under review"},
    "Under review": {"Referred", "Action recorded", "Closed"},
    "Referred": {"Under review", "Action recorded", "Closed"},
    "Action recorded": {"Under review", "Closed"},
    "Closed": {"Under review"},
}


def apply_status_update(
    record: dict,
    *,
    new_status: str,
    review_notes: str,
    changed_at: str,
) -> tuple[dict, dict | None]:
    """Return an updated copy and a status-change event, without mutating input."""
    if new_status not in STATUSES:
        raise ValueError("Unknown case status.")
    current_status = record.get("status")
    if current_status not in STATUSES:
        raise ValueError("The record has an invalid current status.")
    if len(review_notes or "") > 1000:
        raise ValueError("Reviewer notes must be 1,000 characters or fewer.")
    if new_status != current_status and new_status not in ALLOWED_TRANSITIONS[current_status]:
        raise ValueError(f"Status cannot move directly from {current_status} to {new_status}.")

    updated = deepcopy(record)
    updated["status"] = new_status
    updated["review_notes"] = (review_notes or "").strip()
    updated["updated_at"] = changed_at

    event = None
    if new_status != current_status:
        event = {
            "case_id": record.get("case_id", ""),
            "from_status": current_status,
            "to_status": new_status,
            "changed_at": changed_at,
        }
    return updated, event



def apply_case_transition(
    record: Mapping[str, Any],
    *,
    new_status: str,
    actor: str,
    changed_at: str,
    reason: str = "",
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Compatibility-safe audited transition used by the transactional repository."""
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
