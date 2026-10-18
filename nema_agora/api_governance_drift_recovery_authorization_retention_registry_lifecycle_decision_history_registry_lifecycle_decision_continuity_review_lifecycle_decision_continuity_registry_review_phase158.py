"""Phase 158 — human review of Phase 157 registry health."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Mapping
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_continuity_registry_monitor_phase157 import validate_lifecycle_decision_continuity_registry_monitor

POLICY_VERSION = "phase158-v1"
ROLES = ("coordinator", "admin")
OUTCOMES = ("ACKNOWLEDGED", "REVIEW_CONTINUITY", "PRESERVE_AND_ESCALATE", "ESCALATED")

def review_lifecycle_decision_continuity_registry(
    monitor_report: Mapping[str, Any], *, actor_id: str, role: str, outcome: str, reviewed_at: str, notes: str = ""
) -> dict[str, Any]:
    monitor_report = validate_lifecycle_decision_continuity_registry_monitor(monitor_report)
    if not str(actor_id).strip() or role not in ROLES or outcome not in OUTCOMES: raise ValueError("INVALID_REVIEW_ACTOR_ROLE_OR_OUTCOME")
    try: datetime.fromisoformat(str(reviewed_at).replace("Z", "+00:00"))
    except ValueError as exc: raise ValueError("INVALID_REVIEW_TIME") from exc
    allowed = {
        "ACKNOWLEDGED": ("CONTINUITY_HEALTHY",),
        "REVIEW_CONTINUITY": ("NO_HISTORY",),
        "PRESERVE_AND_ESCALATE": ("CONTROL_REQUIRED",),
        "ESCALATED": ("NO_HISTORY", "CONTROL_REQUIRED"),
    }
    if monitor_report["state"] not in allowed[outcome]: raise ValueError("OUTCOME_NOT_ALLOWED_FOR_MONITOR_STATE")
    payload = {
        "policy_version": POLICY_VERSION, "monitor_fingerprint": monitor_report["monitor_fingerprint"],
        "monitor_state": monitor_report["state"], "monitor_recommendation": monitor_report["recommendation"],
        "actor_id": str(actor_id), "role": role, "outcome": outcome, "reviewed_at": reviewed_at,
        "notes": str(notes), "human_governed": True, "automatic_repair_performed": False,
        "execution_gate_closed": True, "execution_permitted": False, "execution_performed": False,
        "environmental_conclusion": None, "regulatory_conclusion": None,
        "enforcement_action": None, "emergency_action": None,
        "interpretation": "LIFECYCLE_DECISION_CONTINUITY_REGISTRY_HUMAN_REVIEW",
    }
    return dict(payload, review_fingerprint=fingerprint(payload))

def validate_lifecycle_decision_continuity_registry_review(review: Mapping[str, Any]) -> dict[str, Any]:
    required = ("policy_version","monitor_fingerprint","monitor_state","monitor_recommendation","actor_id","role","outcome","reviewed_at","notes","human_governed","automatic_repair_performed","execution_gate_closed","execution_permitted","execution_performed","review_fingerprint")
    if not isinstance(review, Mapping) or any(k not in review for k in required): raise ValueError("REVIEW_FIELDS_REQUIRED")
    if review["policy_version"] != POLICY_VERSION or review["role"] not in ROLES or review["outcome"] not in OUTCOMES: raise ValueError("INVALID_REVIEW_POLICY")
    allowed = {"ACKNOWLEDGED":("CONTINUITY_HEALTHY",),"REVIEW_CONTINUITY":("NO_HISTORY",),"PRESERVE_AND_ESCALATE":("CONTROL_REQUIRED",),"ESCALATED":("NO_HISTORY","CONTROL_REQUIRED")}
    if review["monitor_state"] not in allowed[review["outcome"]]: raise ValueError("OUTCOME_STATE_MISMATCH")
    if not str(review["actor_id"]).strip(): raise ValueError("ACTOR_REQUIRED")
    try: datetime.fromisoformat(str(review["reviewed_at"]).replace("Z", "+00:00"))
    except ValueError as exc: raise ValueError("INVALID_REVIEW_TIME") from exc
    if review["human_governed"] is not True or review["automatic_repair_performed"] is not False: raise ValueError("INVALID_REVIEW_CONTROLS")
    if review["execution_gate_closed"] is not True or review["execution_permitted"] is not False or review["execution_performed"] is not False: raise ValueError("EXECUTION_GATE_VIOLATION")
    payload = dict(review); supplied = payload.pop("review_fingerprint")
    if fingerprint(payload) != supplied: raise ValueError("REVIEW_FINGERPRINT_MISMATCH")
    return dict(review)
