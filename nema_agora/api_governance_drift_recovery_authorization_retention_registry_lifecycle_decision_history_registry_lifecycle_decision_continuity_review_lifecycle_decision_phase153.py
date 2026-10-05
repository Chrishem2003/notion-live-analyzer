"""Phase 153 — human authorization boundary for Phase 152 review lifecycles."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Mapping
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_phase152 import validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle

POLICY_VERSION = "phase153-v1"
DECISIONS = ("AUTHORIZE_REVIEW", "AUTHORIZE_PRESERVATION", "AUTHORIZE_ESCALATION")
ROLES = ("coordinator", "admin")
ALLOWED_STATES = {
    "AUTHORIZE_REVIEW": ("DEFERRED",),
    "AUTHORIZE_PRESERVATION": ("ACKNOWLEDGED", "DEFERRED"),
    "AUTHORIZE_ESCALATION": ("ESCALATED",),
}

def authorize_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(
    lifecycle: Mapping[str, Any], *, actor_id: str, role: str, decision: str,
    decided_at: str, rationale: str
) -> dict[str, Any]:
    lifecycle = validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(lifecycle)
    if not str(actor_id).strip() or role not in ROLES or decision not in DECISIONS:
        raise ValueError("INVALID_AUTHORIZATION_ACTOR_ROLE_OR_DECISION")
    try:
        datetime.fromisoformat(str(decided_at).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_DECISION_TIME") from exc
    if not str(rationale).strip():
        raise ValueError("RATIONALE_REQUIRED")
    if lifecycle["state"] not in ALLOWED_STATES[decision]:
        raise ValueError("DECISION_NOT_ALLOWED_FOR_LIFECYCLE_STATE")
    payload = {
        "policy_version": POLICY_VERSION,
        "lifecycle_fingerprint": lifecycle["lifecycle_fingerprint"],
        "review_fingerprint": lifecycle["review_fingerprint"],
        "monitor_fingerprint": lifecycle["monitor_fingerprint"],
        "lifecycle_state": lifecycle["state"],
        "lifecycle_outcome": lifecycle["outcome"],
        "actor_id": str(actor_id),
        "role": role,
        "decision": decision,
        "decided_at": decided_at,
        "rationale": str(rationale),
        "human_authorized": True,
        "automatic_repair_performed": False,
        "execution_gate_closed": True,
        "execution_permitted": False,
        "execution_performed": False,
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
        "emergency_action": None,
    }
    return dict(payload, decision_fingerprint=fingerprint(payload))

def validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision(
    decision: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(decision, Mapping):
        raise ValueError("INVALID_DECISION")
    required = (
        "policy_version", "lifecycle_fingerprint", "review_fingerprint", "monitor_fingerprint",
        "lifecycle_state", "lifecycle_outcome", "actor_id", "role", "decision", "decided_at",
        "rationale", "human_authorized", "automatic_repair_performed", "execution_gate_closed",
        "execution_permitted", "execution_performed", "decision_fingerprint",
    )
    if any(k not in decision for k in required):
        raise ValueError("DECISION_FIELDS_REQUIRED")
    if decision["policy_version"] != POLICY_VERSION or decision["decision"] not in DECISIONS or decision["role"] not in ROLES:
        raise ValueError("INVALID_DECISION_POLICY")
    if decision["lifecycle_state"] not in ALLOWED_STATES[decision["decision"]]:
        raise ValueError("DECISION_STATE_MISMATCH")
    if not str(decision["actor_id"]).strip() or not str(decision["rationale"]).strip():
        raise ValueError("ACTOR_AND_RATIONALE_REQUIRED")
    try:
        datetime.fromisoformat(str(decision["decided_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_DECISION_TIME") from exc
payload = dict(decision)
    supplied = payload.pop("decision_fingerprint")
    if fingerprint(payload) != supplied:
        raise ValueError("DECISION_FINGERPRINT_MISMATCH")\n    if decision["human_authorized"] is not True:\n        raise ValueError("HUMAN_AUTHORIZATION_REQUIRED")
    if decision["automatic_repair_performed"] is not False:
        raise ValueError("AUTOMATIC_REPAIR_FORBIDDEN")
    if decision["execution_gate_closed"] is not True or decision["execution_permitted"] is not False or decision["execution_performed"] is not False:
        raise ValueError("EXECUTION_GATE_VIOLATION")
    for key in ("environmental_conclusion", "regulatory_conclusion", "enforcement_action", "emergency_action"):
        if decision.get(key) is not None:
            raise ValueError("PROHIBITED_CONCLUSION_OR_ACTION")
    payload = dict(decision)
    supplied = payload.pop("decision_fingerprint")
    if fingerprint(payload) != supplied:
        raise ValueError("DECISION_FINGERPRINT_MISMATCH")
    return dict(decision)
