"""Phase 142 — human-governed review of Phase 141 decision-history registry integrity evidence."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_monitor_phase141 import (
    validate_authorization_history_registry_decision_history_monitor,
)

POLICY_VERSION = "phase142-v1"
OUTCOMES = (
    "ACKNOWLEDGED",
    "REVIEW_AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY",
    "PRESERVE_AND_ESCALATE",
    "ESCALATED",
)
ROLES = ("coordinator", "admin")


def validate_decision_history_monitor(report: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return validate_authorization_history_registry_decision_history_monitor(report)
    except ValueError as exc:
        raise ValueError(f"INVALID_AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY_MONITOR:{exc}") from exc


def review_authorization_history_registry_decision_history(
    monitor_report: Mapping[str, Any],
    *,
    actor_id: str,
    role: str,
    outcome: str,
    reviewed_at: str,
    notes: str = "",
) -> dict[str, Any]:
    """Record an explicitly human decision about Phase 141 integrity evidence."""
    monitor = validate_decision_history_monitor(monitor_report)
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise ValueError("ACTOR_ID_REQUIRED")
    if role not in ROLES:
        raise ValueError("INVALID_ROLE")
    if outcome not in OUTCOMES:
        raise ValueError("INVALID_OUTCOME")
    if not isinstance(reviewed_at, str) or not reviewed_at.strip():
        raise ValueError("REVIEW_TIME_REQUIRED")
    try:
        datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_REVIEW_TIME") from exc
    if outcome == "ACKNOWLEDGED" and monitor["state"] != "RETENTION_REGISTRY_HEALTHY":
        raise ValueError("ACKNOWLEDGED_REQUIRES_HEALTHY_REGISTRY")
    if (
        outcome == "REVIEW_AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY"
        and monitor["state"] not in ("NO_HISTORY", "CONTROL_REQUIRED")
    ):
        raise ValueError("REVIEW_DECISION_HISTORY_REQUIRES_REVIEW_STATE")
    if outcome == "PRESERVE_AND_ESCALATE" and monitor["state"] != "CONTROL_REQUIRED":
        raise ValueError("PRESERVE_AND_ESCALATE_REQUIRES_CONTROL")
    if outcome == "ESCALATED" and monitor["state"] not in ("NO_HISTORY", "CONTROL_REQUIRED"):
        raise ValueError("ESCALATED_REQUIRES_REVIEW_STATE")
    if not isinstance(notes, str):
        raise ValueError("INVALID_REVIEW_NOTES")

    payload = {
        "policy_version": POLICY_VERSION,
        "monitor_fingerprint": monitor["monitor_fingerprint"],
        "monitor_state": monitor["state"],
        "retention_registry_recommendation": monitor["retention_registry_recommendation"],
        "actor_id": actor_id.strip(),
        "role": role,
        "outcome": outcome,
        "reviewed_at": reviewed_at,
        "notes": notes.strip(),
        "human_governed": True,
        "automatic_repair_performed": False,
        "execution_gate_closed": True,
        "execution_permitted": False,
        "execution_performed": False,
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
        "emergency_action": None,
    }
    return dict(payload, review_fingerprint=fingerprint(payload))


def validate_authorization_history_registry_decision_history_review(
    review: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(review, Mapping):
        raise ValueError("INVALID_AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY_REVIEW")
    required = (
        "policy_version", "monitor_fingerprint", "monitor_state",
        "retention_registry_recommendation", "actor_id", "role", "outcome",
        "reviewed_at", "notes", "human_governed", "automatic_repair_performed",
        "execution_gate_closed", "execution_permitted", "execution_performed",
        "review_fingerprint",
    )
    for key in required:
        if key not in review:
            raise ValueError("REVIEW_FIELDS_REQUIRED")
    if review["policy_version"] != POLICY_VERSION or review["role"] not in ROLES:
        raise ValueError("INVALID_REVIEW_POLICY_OR_ROLE")
    if review["outcome"] not in OUTCOMES:
        raise ValueError("INVALID_REVIEW_OUTCOME")
    if review["human_governed"] is not True or review["automatic_repair_performed"] is not False:
        raise ValueError("INVALID_REVIEW_CONTROLS")
    if (
        review["execution_gate_closed"] is not True
        or review["execution_permitted"] is not False
        or review["execution_performed"] is not False
    ):
        raise ValueError("EXECUTION_GATE_VIOLATION")
    if not isinstance(review["actor_id"], str) or not review["actor_id"].strip():
        raise ValueError("ACTOR_ID_REQUIRED")
    if not isinstance(review["notes"], str):
        raise ValueError("INVALID_REVIEW_NOTES")
    try:
        datetime.fromisoformat(str(review["reviewed_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_REVIEW_TIME") from exc
    payload = dict(review)
    supplied = payload.pop("review_fingerprint")
    if fingerprint(payload) != supplied:
        raise ValueError("REVIEW_FINGERPRINT_MISMATCH")
    return dict(review)
