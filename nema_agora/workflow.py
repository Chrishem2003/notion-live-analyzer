"""Small, testable status-transition rules for the NEMA-AGORA pilot.

This is a workflow safeguard, not an authenticated audit system. Actor identity,
durable logging, and role-based permissions must be added before multi-user use.
"""
from __future__ import annotations

from copy import deepcopy

from nema_agora.core import STATUSES

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
