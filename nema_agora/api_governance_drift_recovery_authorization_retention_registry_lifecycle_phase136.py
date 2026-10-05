"""Phase 136 — lifecycle governance for Phase 134 authorization-history registry reviews."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Mapping, Sequence
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_review_phase134 import validate_authorization_history_registry_review
from .api_governance_drift_recovery_authorization_retention_registry_review_reconciliation_phase135 import validate_authorization_history_registry_review_reconciliation

POLICY_VERSION="phase136-v1"
STATES=("OPEN","ACKNOWLEDGED","DEFERRED","ESCALATED")
OUTCOMES=("ACKNOWLEDGED","REVIEW_AUTHORIZATION_HISTORY_REGISTRY","PRESERVE_AND_ESCALATE","ESCALATED")

def _validate_time(value:Any,field:str)->None:
    if not isinstance(value,str) or not value.strip(): raise ValueError(f"{field}_REQUIRED")
    try: datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc: raise ValueError(f"INVALID_{field}") from exc

def evaluate_authorization_history_registry_review_lifecycle(review:Mapping[str,Any],*,evaluated_at:str)->dict[str,Any]:
    validated=validate_authorization_history_registry_review(review); _validate_time(evaluated_at,"EVALUATION_TIME")
    state={"ACKNOWLEDGED":"ACKNOWLEDGED","REVIEW_AUTHORIZATION_HISTORY_REGISTRY":"DEFERRED","PRESERVE_AND_ESCALATE":"ESCALATED","ESCALATED":"ESCALATED"}[validated["outcome"]]
    payload={"policy_version":POLICY_VERSION,"monitor_fingerprint":validated["monitor_fingerprint"],"review_fingerprint":validated["review_fingerprint"],"review_outcome":validated["outcome"],"lifecycle_state":state,"evaluated_at":evaluated_at,"human_governed":True,"automatic_repair_performed":False,"decision_executed":False,"execution_gate_closed":True,"execution_permitted":False,"execution_performed":False,"environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None,"emergency_action":None}
    return dict(payload,lifecycle_fingerprint=fingerprint(payload))

def validate_authorization_history_registry_lifecycle(lifecycle:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(lifecycle,Mapping): raise ValueError("INVALID_AUTHORIZATION_HISTORY_REGISTRY_LIFECYCLE")
    required=("policy_version","monitor_fingerprint","review_fingerprint","review_outcome","lifecycle_state","evaluated_at","human_governed","automatic_repair_performed","decision_executed","execution_gate_closed","execution_permitted","execution_performed","lifecycle_fingerprint")
    for key in required:
        if key not in lifecycle: raise ValueError(f"MISSING_{key.upper()}")
    if lifecycle["policy_version"]!=POLICY_VERSION: raise ValueError("INVALID_LIFECYCLE_POLICY")
    if lifecycle["review_outcome"] not in OUTCOMES: raise ValueError("INVALID_LIFECYCLE_OUTCOME")
    expected={"ACKNOWLEDGED":"ACKNOWLEDGED","REVIEW_AUTHORIZATION_HISTORY_REGISTRY":"DEFERRED","PRESERVE_AND_ESCALATE":"ESCALATED","ESCALATED":"ESCALATED"}[lifecycle["review_outcome"]]
    if lifecycle["lifecycle_state"]!=expected: raise ValueError("LIFECYCLE_STATE_OUTCOME_MISMATCH")
    if lifecycle["human_governed"] is not True: raise ValueError("INVALID_LIFECYCLE_GOVERNANCE")
    if lifecycle["automatic_repair_performed"] is not False: raise ValueError("INVALID_LIFECYCLE_REPAIR_CONTROL")
    if lifecycle["decision_executed"] is not False: raise ValueError("INVALID_DECISION_EXECUTION_CONTROL")
    if lifecycle["execution_gate_closed"] is not True or lifecycle["execution_permitted"] is not False or lifecycle["execution_performed"] is not False: raise ValueError("INVALID_EXECUTION_CONTROLS")
    _validate_time(lifecycle["evaluated_at"],"EVALUATION_TIME")
    payload=dict(lifecycle); supplied=payload.pop("lifecycle_fingerprint")
    if fingerprint(payload)!=supplied: raise ValueError("AUTHORIZATION_HISTORY_REGISTRY_LIFECYCLE_FINGERPRINT_MISMATCH")
    return dict(lifecycle)

def build_authorization_history_registry_review_lifecycle(reconciliation:Mapping[str,Any],reviews:Sequence[Mapping[str,Any]],*,evaluated_at:str)->dict[str,Any]:
    rec=validate_authorization_history_registry_review_reconciliation(reconciliation)
    if rec["state"]!="RECONCILED": raise ValueError("RECONCILIATION_MUST_BE_RECONCILED")
    if not isinstance(reviews,Sequence) or isinstance(reviews,(str,bytes)) or not reviews: raise ValueError("AUTHORIZATION_HISTORY_REGISTRY_REVIEWS_REQUIRED")
    lifecycles=[evaluate_authorization_history_registry_review_lifecycle(review,evaluated_at=evaluated_at) for review in reviews]
    payload={"policy_version":POLICY_VERSION,"evaluated_at":evaluated_at,"reconciliation_fingerprint":rec["reconciliation_fingerprint"],"lifecycle_count":len(lifecycles),"lifecycles":lifecycles,"human_governed":True,"automatic_repair_performed":False,"execution_gate_closed":True,"execution_permitted":False,"execution_performed":False,"interpretation":"AUTHORIZATION_HISTORY_REGISTRY_REVIEW_LIFECYCLE_GOVERNANCE","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None,"emergency_action":None}
    return dict(payload,lifecycle_fingerprint=fingerprint(payload))

def validate_authorization_history_registry_lifecycle_bundle(bundle:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(bundle,Mapping): raise ValueError("INVALID_AUTHORIZATION_HISTORY_REGISTRY_LIFECYCLE_BUNDLE")
    required=("policy_version","evaluated_at","reconciliation_fingerprint","lifecycle_count","lifecycles","human_governed","automatic_repair_performed","execution_gate_closed","execution_permitted","execution_performed","lifecycle_fingerprint")
    for key in required:
        if key not in bundle: raise ValueError(f"MISSING_{key.upper()}")
    if bundle["policy_version"]!=POLICY_VERSION: raise ValueError("INVALID_BUNDLE_POLICY")
    if bundle["human_governed"] is not True or bundle["automatic_repair_performed"] is not False: raise ValueError("INVALID_BUNDLE_GOVERNANCE")
    if bundle["execution_gate_closed"] is not True or bundle["execution_permitted"] is not False or bundle["execution_performed"] is not False: raise ValueError("INVALID_BUNDLE_EXECUTION_CONTROLS")
    _validate_time(bundle["evaluated_at"],"EVALUATION_TIME")
    if not isinstance(bundle["lifecycles"],list) or bundle["lifecycle_count"]!=len(bundle["lifecycles"]): raise ValueError("LIFECYCLE_COUNT_MISMATCH")
    for lifecycle in bundle["lifecycles"]: validate_authorization_history_registry_lifecycle(lifecycle)
    payload=dict(bundle); supplied=payload.pop("lifecycle_fingerprint")
    if fingerprint(payload)!=supplied: raise ValueError("AUTHORIZATION_HISTORY_REGISTRY_LIFECYCLE_BUNDLE_FINGERPRINT_MISMATCH")
    return dict(bundle)
