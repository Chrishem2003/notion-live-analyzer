"""Phase 118 — human-governed review of authorization-retention health evidence."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_monitor import (
    build_authorization_retention_monitor,
)

POLICY_VERSION = "phase118-v1"
OUTCOMES = ("ACKNOWLEDGED", "REVIEW_RETENTION", "PRESERVE_AND_ESCALATE", "ESCALATED")
ROLES = ("coordinator", "admin")


def validate_retention_monitor(report: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "policy_version", "observed_at", "state", "snapshot_count",
        "valid_snapshot_count", "findings", "retention_recommendation",
        "read_only", "automatic_repair_performed", "execution_gate_closed",
        "monitor_fingerprint",
    )
    if not isinstance(report, Mapping):
        raise ValueError("INVALID_RETENTION_MONITOR")
    for key in required:
        if key not in report:
            raise ValueError(f"MISSING_{key.upper()}")
    if report["policy_version"] != "phase117-v1":
        raise ValueError("INVALID_MONITOR_POLICY")
    if report["state"] not in ("RETENTION_HEALTHY", "NO_HISTORY", "CONTROL_REQUIRED"):
        raise ValueError("INVALID_MONITOR_STATE")
    if report["retention_recommendation"] not in (
        "NO_RETENTION_ACTION", "REVIEW_RETENTION", "PRESERVE_AND_ESCALATE"
    ):
        raise ValueError("INVALID_RETENTION_RECOMMENDATION")
    if report["read_only"] is not True or report["automatic_repair_performed"] is not False:
        raise ValueError("INVALID_MONITOR_CONTROLS")
    if report["execution_gate_closed"] is not True:
        raise ValueError("EXECUTION_GATE_MUST_BE_CLOSED")
    if not isinstance(report["findings"], list):
        raise ValueError("INVALID_MONITOR_FINDINGS")
    try:
        datetime.fromisoformat(str(report["observed_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_OBSERVATION_TIME") from exc
    payload = dict(report)
    supplied = payload.pop("monitor_fingerprint")
    if fingerprint(payload) != supplied:
        raise ValueError("RETENTION_MONITOR_FINGERPRINT_MISMATCH")
    return dict(report)


def review_retention_health(
    monitor_report: Mapping[str, Any],
    *,
    actor_id: str,
    role: str,
    outcome: str,
    reviewed_at: str,
    notes: str = "",
) -> dict[str, Any]:
    monitor = validate_retention_monitor(monitor_report)
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
    if outcome == "ACKNOWLEDGED" and monitor["state"] != "RETENTION_HEALTHY":
        raise ValueError("ACKNOWLEDGED_REQUIRES_HEALTHY_RETENTION")
    if outcome == "REVIEW_RETENTION" and monitor["state"] not in ("NO_HISTORY", "CONTROL_REQUIRED"):
        raise ValueError("REVIEW_RETENTION_REQUIRES_REVIEW_STATE")
    if outcome == "PRESERVE_AND_ESCALATE" and monitor["state"] != "CONTROL_REQUIRED":
        raise ValueError("PRESERVE_AND_ESCALATE_REQUIRES_CONTROL")
    if not isinstance(notes, str):
        raise ValueError("INVALID_REVIEW_NOTES")

    payload = {
        "policy_version": POLICY_VERSION,
        "monitor_fingerprint": monitor["monitor_fingerprint"],
        "monitor_state": monitor["state"],
        "retention_recommendation": monitor["retention_recommendation"],
        "actor_id": actor_id.strip(),
        "role": role,
        "outcome": outcome,
        "reviewed_at": reviewed_at,
        "notes": notes.strip(),
        "human_governed": True,
        "automatic_repair_performed": False,
        "execution_gate_closed": True,
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
    }
    return dict(payload, review_fingerprint=fingerprint(payload))


def validate_retention_review(review: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "policy_version", "monitor_fingerprint", "monitor_state",
        "retention_recommendation", "actor_id", "role", "outcome",
        "reviewed_at", "notes", "human_governed",
        "automatic_repair_performed", "execution_gate_closed",
        "review_fingerprint",
    )
    if not isinstance(review, Mapping):
        raise ValueError("INVALID_RETENTION_REVIEW")
    for key in required:
        if key not in review:
            raise ValueError(f"MISSING_{key.upper()}")
    if review["policy_version"] != POLICY_VERSION or review["role"] not in ROLES:
        raise ValueError("INVALID_RETENTION_REVIEW_POLICY_OR_ROLE")
    if review["outcome"] not in OUTCOMES:
        raise ValueError("INVALID_RETENTION_REVIEW_OUTCOME")
    if review["human_governed"] is not True or review["automatic_repair_performed"] is not False:
        raise ValueError("INVALID_RETENTION_REVIEW_CONTROLS")
    if review["execution_gate_closed"] is not True:
        raise ValueError("EXECUTION_GATE_MUST_BE_CLOSED")
    payload = dict(review)
    supplied = payload.pop("review_fingerprint")
    if fingerprint(payload) != supplied:
        raise ValueError("RETENTION_REVIEW_FINGERPRINT_MISMATCH")
    return dict(review)
