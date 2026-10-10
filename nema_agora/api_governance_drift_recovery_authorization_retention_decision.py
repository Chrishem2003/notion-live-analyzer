"""Phase 121 — explicit human authorization for retention governance decisions."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Mapping
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_lifecycle import validate_retention_lifecycle

POLICY_VERSION = "phase121-v1"
DECISIONS = ("AUTHORIZE_RETENTION_REVIEW", "AUTHORIZE_PRESERVATION", "AUTHORIZE_ESCALATION")
ROLES = ("coordinator", "admin")

def authorize_retention_decision(lifecycle: Mapping[str, Any], *, actor_id: str, role: str, decision: str, decided_at: str, rationale: str) -> dict[str, Any]:
    state = validate_retention_lifecycle(lifecycle)
    if not isinstance(actor_id, str) or not actor_id.strip(): raise ValueError("ACTOR_ID_REQUIRED")
    if role not in ROLES: raise ValueError("INVALID_ROLE")
    if decision not in DECISIONS: raise ValueError("INVALID_DECISION")
    if not isinstance(decided_at, str) or not decided_at.strip(): raise ValueError("DECISION_TIME_REQUIRED")
    try: datetime.fromisoformat(decided_at.replace("Z", "+00:00"))
    except ValueError as exc: raise ValueError("INVALID_DECISION_TIME") from exc
    if not isinstance(rationale, str) or not rationale.strip(): raise ValueError("RATIONALE_REQUIRED")
    if decision == "AUTHORIZE_RETENTION_REVIEW" and state["lifecycle_state"] != "DEFERRED": raise ValueError("RETENTION_REVIEW_REQUIRES_DEFERRED")
    if decision == "AUTHORIZE_PRESERVATION" and state["lifecycle_state"] not in ("ACKNOWLEDGED", "DEFERRED"): raise ValueError("PRESERVATION_REQUIRES_ACKNOWLEDGED_OR_DEFERRED")
    if decision == "AUTHORIZE_ESCALATION" and state["lifecycle_state"] != "ESCALATED": raise ValueError("ESCALATION_REQUIRES_ESCALATED")
    payload = {
        "policy_version": POLICY_VERSION, "monitor_fingerprint": state["monitor_fingerprint"],
        "review_fingerprint": state["review_fingerprint"], "lifecycle_fingerprint": state["lifecycle_fingerprint"],
        "lifecycle_state": state["lifecycle_state"], "actor_id": actor_id.strip(), "role": role,
        "decision": decision, "decided_at": decided_at, "rationale": rationale.strip(),
        "human_authorized": True, "execution_permitted": False, "execution_performed": False,
        "automatic_repair_performed": False, "execution_gate_closed": True,
        "environmental_conclusion": None, "regulatory_conclusion": None, "enforcement_action": None,
    }
    return dict(payload, decision_fingerprint=fingerprint(payload))

def validate_retention_decision(decision: Mapping[str, Any]) -> dict[str, Any]:
    required = ("policy_version","monitor_fingerprint","review_fingerprint","lifecycle_fingerprint","lifecycle_state","actor_id","role","decision","decided_at","rationale","human_authorized","execution_permitted","execution_performed","automatic_repair_performed","execution_gate_closed","decision_fingerprint")
    if not isinstance(decision, Mapping): raise ValueError("INVALID_RETENTION_DECISION")
    for key in required:
        if key not in decision: raise ValueError(f"MISSING_{key.upper()}")
    payload = dict(decision); supplied = payload.pop("decision_fingerprint")
    if fingerprint(payload) != supplied: raise ValueError("RETENTION_DECISION_FINGERPRINT_MISMATCH")
    if decision["policy_version"] != POLICY_VERSION: raise ValueError("INVALID_DECISION_POLICY")
    if decision["role"] not in ROLES or decision["decision"] not in DECISIONS: raise ValueError("INVALID_DECISION_ROLE_OR_VALUE")
    if decision["human_authorized"] is not True: raise ValueError("HUMAN_AUTHORIZATION_REQUIRED")
    if decision["execution_permitted"] is not False or decision["execution_performed"] is not False: raise ValueError("EXECUTION_MUST_REMAIN_CLOSED")
    if decision["automatic_repair_performed"] is not False or decision["execution_gate_closed"] is not True: raise ValueError("INVALID_DECISION_CONTROLS")
    return dict(decision)
