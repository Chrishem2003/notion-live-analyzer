"""Phase 145 — explicit human authorization boundary for Phase 144 lifecycles."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Mapping
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_review_lifecycle_phase144 import validate_authorization_history_registry_decision_history_review_lifecycle

POLICY_VERSION = "phase145-v1"
DECISIONS = ("AUTHORIZE_REVIEW", "AUTHORIZE_PRESERVATION", "AUTHORIZE_ESCALATION")
ROLES = ("coordinator", "admin")

def _validate_time(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_REQUIRED")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"INVALID_{field}") from exc

def authorize_authorization_history_registry_decision_history_lifecycle(
    lifecycle: Mapping[str, Any],
    *,
    actor_id: str,
    role: str,
    decision: str,
    decided_at: str,
    rationale: str,
) -> dict[str, Any]:
    item = validate_authorization_history_registry_decision_history_review_lifecycle(lifecycle)
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise ValueError("ACTOR_ID_REQUIRED")
    if role not in ROLES:
        raise ValueError("INVALID_ROLE")
    if decision not in DECISIONS:
        raise ValueError("INVALID_DECISION")
    _validate_time(decided_at, "DECISION_TIME")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("RATIONALE_REQUIRED")
    state = item["lifecycle_state"]
    allowed = {
        "AUTHORIZE_REVIEW": {"DEFERRED"},
        "AUTHORIZE_PRESERVATION": {"ACKNOWLEDGED", "DEFERRED"},
        "AUTHORIZE_ESCALATION": {"ESCALATED"},
    }
    if state not in allowed[decision]:
        raise ValueError("DECISION_STATE_MISMATCH")
    payload = {
        "policy_version": POLICY_VERSION,
        "monitor_fingerprint": item["monitor_fingerprint"],
        "review_fingerprint": item["review_fingerprint"],
        "lifecycle_fingerprint": item["lifecycle_fingerprint"],
        "lifecycle_state": state,
        "actor_id": actor_id.strip(),
        "role": role,
        "decision": decision,
        "decided_at": decided_at,
        "rationale": rationale.strip(),
        "human_authorized": True,
        "execution_permitted": False,
        "execution_performed": False,
        "automatic_repair_performed": False,
        "execution_gate_closed": True,
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
        "emergency_action": None,
    }
    return dict(payload, decision_fingerprint=fingerprint(payload))

def validate_authorization_history_registry_decision_history_lifecycle_decision(
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(decision, Mapping):
        raise ValueError("INVALID_LIFECYCLE_DECISION")
    required = (
        "policy_version","monitor_fingerprint","review_fingerprint","lifecycle_fingerprint",
        "lifecycle_state","actor_id","role","decision","decided_at","rationale",
        "human_authorized","execution_permitted","execution_performed",
        "automatic_repair_performed","execution_gate_closed","decision_fingerprint",
    )
    for key in required:
        if key not in decision:
            raise ValueError("DECISION_FIELDS_REQUIRED")
    if decision["policy_version"] != POLICY_VERSION or decision["role"] not in ROLES:
        raise ValueError("INVALID_DECISION_POLICY_OR_ROLE")
    if decision["decision"] not in DECISIONS:
        raise ValueError("INVALID_DECISION")
    allowed = {
        "AUTHORIZE_REVIEW": {"DEFERRED"},
        "AUTHORIZE_PRESERVATION": {"ACKNOWLEDGED", "DEFERRED"},
        "AUTHORIZE_ESCALATION": {"ESCALATED"},
    }
    if decision["lifecycle_state"] not in allowed[decision["decision"]]:
        raise ValueError("DECISION_STATE_MISMATCH")
    if decision["human_authorized"] is not True:
        raise ValueError("HUMAN_AUTHORIZATION_REQUIRED")
    if decision["execution_permitted"] is not False or decision["execution_performed"] is not False:
        raise ValueError("EXECUTION_FORBIDDEN")
    if decision["automatic_repair_performed"] is not False or decision["execution_gate_closed"] is not True:
        raise ValueError("INVALID_EXECUTION_CONTROLS")
    if not isinstance(decision["actor_id"], str) or not decision["actor_id"].strip():
        raise ValueError("ACTOR_ID_REQUIRED")
    if not isinstance(decision["rationale"], str) or not decision["rationale"].strip():
        raise ValueError("RATIONALE_REQUIRED")
    _validate_time(decision["decided_at"], "DECISION_TIME")
    payload = dict(decision)
    supplied = payload.pop("decision_fingerprint")
    if fingerprint(payload) != supplied:
        raise ValueError("DECISION_FINGERPRINT_MISMATCH")
    return dict(decision)
