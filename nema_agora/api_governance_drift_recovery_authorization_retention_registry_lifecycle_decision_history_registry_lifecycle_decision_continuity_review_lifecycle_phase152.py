"""Phase 152 — lifecycle for Phase 151 continuity review reconciliation."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Mapping
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_reconciliation_phase151 import validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_reconciliation
POLICY_VERSION="phase152-v1"
STATES=("OPEN","ACKNOWLEDGED","DEFERRED","ESCALATED")
OUTCOMES=("ACKNOWLEDGED","REVIEW_CONTINUITY","PRESERVE_AND_ESCALATE","ESCALATED")
ROLES=("coordinator","admin")
MAPPING={"ACKNOWLEDGED":"ACKNOWLEDGED","REVIEW_CONTINUITY":"DEFERRED","PRESERVE_AND_ESCALATE":"ESCALATED","ESCALATED":"ESCALATED"}

def evaluate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(review: Mapping[str,Any], *, evaluated_at: str)->dict[str,Any]:
    if not isinstance(review,Mapping): raise ValueError("INVALID_REVIEW")
    if review.get("outcome") not in OUTCOMES: raise ValueError("INVALID_REVIEW_OUTCOME")
    try: datetime.fromisoformat(str(evaluated_at).replace("Z","+00:00"))
    except ValueError as exc: raise ValueError("INVALID_EVALUATION_TIME") from exc
    validate_fields=(
        "review_fingerprint","monitor_fingerprint","monitor_state","monitor_recommendation",
        "outcome","human_governed","automatic_repair_performed","execution_gate_closed",
        "execution_permitted","execution_performed")
    if any(k not in review for k in validate_fields): raise ValueError("REVIEW_FIELDS_REQUIRED")
    state=MAPPING[review["outcome"]]
    payload={"policy_version":POLICY_VERSION,"review_fingerprint":review["review_fingerprint"],"monitor_fingerprint":review["monitor_fingerprint"],"monitor_state":review["monitor_state"],"monitor_recommendation":review["monitor_recommendation"],"outcome":review["outcome"],"state":state,"evaluated_at":evaluated_at,"human_governed":True,"automatic_repair_performed":False,"execution_gate_closed":True,"execution_permitted":False,"execution_performed":False,"environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None,"emergency_action":None}
    return dict(payload,lifecycle_fingerprint=fingerprint(payload))

def validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(lifecycle: Mapping[str,Any])->dict[str,Any]:
    if not isinstance(lifecycle,Mapping): raise ValueError("INVALID_LIFECYCLE")
    required=("policy_version","review_fingerprint","monitor_fingerprint","monitor_state","monitor_recommendation","outcome","state","evaluated_at","human_governed","automatic_repair_performed","execution_gate_closed","execution_permitted","execution_performed","lifecycle_fingerprint")
    for k in required:
        if k not in lifecycle: raise ValueError("LIFECYCLE_FIELDS_REQUIRED")
    if lifecycle["policy_version"]!=POLICY_VERSION or lifecycle["state"] not in STATES or lifecycle["outcome"] not in OUTCOMES or MAPPING[lifecycle["outcome"]]!=lifecycle["state"]: raise ValueError("INVALID_LIFECYCLE_POLICY_STATE")
    try: datetime.fromisoformat(str(lifecycle["evaluated_at"]).replace("Z","+00:00"))
    except ValueError as exc: raise ValueError("INVALID_EVALUATION_TIME") from exc
    if lifecycle["human_governed"] is not True or lifecycle["automatic_repair_performed"] is not False: raise ValueError("INVALID_LIFECYCLE_CONTROLS")
    if lifecycle["execution_gate_closed"] is not True or lifecycle["execution_permitted"] is not False or lifecycle["execution_performed"] is not False: raise ValueError("EXECUTION_GATE_VIOLATION")
    payload=dict(lifecycle); supplied=payload.pop("lifecycle_fingerprint")
    if fingerprint(payload)!=supplied: raise ValueError("LIFECYCLE_FINGERPRINT_MISMATCH")
    return dict(lifecycle)

def build_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(reconciliation: Mapping[str,Any], reviews: list[Mapping[str,Any]]|tuple[Mapping[str,Any],...], *, evaluated_at: str)->list[dict[str,Any]]:
    reconciliation=validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_reconciliation(reconciliation)
    if reconciliation["state"]!="RECONCILED": raise ValueError("RECONCILIATION_MUST_BE_RECONCILED")
    lifecycles=[]
    for review in reviews:
        if not isinstance(review,Mapping): raise ValueError("INVALID_REVIEW")
        # Phase 150 validation is intentionally delegated by reconciliation; lifecycle remains bound to exact review evidence.
        lifecycles.append(evaluate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(review,evaluated_at=evaluated_at))
    if len(lifecycles)!=reconciliation["valid_review_count"]: raise ValueError("REVIEW_COUNT_MISMATCH")
    return lifecycles
