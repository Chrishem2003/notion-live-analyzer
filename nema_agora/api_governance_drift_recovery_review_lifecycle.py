"""Phase 112 — human-governed lifecycle evaluation for recovery reviews."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Mapping
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_review_ledger import validate_recovery_review
from .api_governance_drift_recovery_review_reconciliation import reconcile_recovery_reviews
POLICY_VERSION="phase112-v1"
STATES=("OPEN","ACKNOWLEDGED","DEFERRED","ESCALATED","APPROVED_NO_ACTION")
OUTCOMES=("ACKNOWLEDGED","BACKUP_REVIEWED","RECOVERY_DEFERRED","ESCALATED","NO_ACTION_APPROVED")
def evaluate_recovery_review_lifecycle(review: Mapping[str,Any], *, evaluated_at: str) -> dict[str,Any]:
    if not isinstance(review,Mapping): raise ValueError("INVALID_REVIEW")
    record=validate_recovery_review(review)
    if not isinstance(evaluated_at,str) or not evaluated_at.strip(): raise ValueError("EVALUATION_TIME_REQUIRED")
    try: datetime.fromisoformat(evaluated_at.replace("Z","+00:00"))
    except ValueError as exc: raise ValueError("INVALID_EVALUATION_TIME") from exc
    outcome=record["outcome"]
    state={"ACKNOWLEDGED":"ACKNOWLEDGED","BACKUP_REVIEWED":"ACKNOWLEDGED","RECOVERY_DEFERRED":"DEFERRED","ESCALATED":"ESCALATED","NO_ACTION_APPROVED":"APPROVED_NO_ACTION"}[outcome]
    payload={"policy_version":POLICY_VERSION,"review_audit_id":record["review_audit_id"],"monitor_fingerprint":record["monitor_fingerprint"],"review_outcome":outcome,"lifecycle_state":state,"evaluated_at":evaluated_at,"human_governed":True,"automatic_recovery_performed":False,"decision_executed":False,"interpretation":"HUMAN_GOVERNED_RECOVERY_REVIEW_LIFECYCLE","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None}
    return dict(payload,lifecycle_fingerprint=fingerprint(payload))
def validate_lifecycle(lifecycle: Mapping[str,Any]) -> dict[str,Any]:
    required=("policy_version","review_audit_id","monitor_fingerprint","review_outcome","lifecycle_state","evaluated_at","human_governed","automatic_recovery_performed","decision_executed","lifecycle_fingerprint")
    if not isinstance(lifecycle,Mapping) or any(k not in lifecycle for k in required): raise ValueError("LIFECYCLE_FIELDS_REQUIRED")
    if lifecycle["policy_version"]!=POLICY_VERSION: raise ValueError("INVALID_LIFECYCLE_POLICY")
    if lifecycle["review_outcome"] not in OUTCOMES or lifecycle["lifecycle_state"] not in STATES: raise ValueError("INVALID_LIFECYCLE_VALUE")
    if lifecycle["human_governed"] is not True or lifecycle["automatic_recovery_performed"] is not False or lifecycle["decision_executed"] is not False: raise ValueError("LIFECYCLE_CONTROL_VIOLATION")
    payload={k:lifecycle[k] for k in required if k!="lifecycle_fingerprint"}
    if fingerprint(payload)!=lifecycle["lifecycle_fingerprint"]: raise ValueError("LIFECYCLE_FINGERPRINT_MISMATCH")
    return dict(lifecycle)
def build_recovery_review_lifecycle(reconciliation: Mapping[str,Any], reviews: list[Mapping[str,Any]], *, evaluated_at: str) -> dict[str,Any]:
    if not isinstance(reconciliation,Mapping) or reconciliation.get("state")!="RECONCILED": raise ValueError("RECONCILIATION_REQUIRED")
    actual=reconcile_recovery_reviews([],reviews,expected_ledger_count=len(reviews))
    if actual["state"]!="RECONCILED": raise ValueError("RECONCILIATION_BINDING_MISMATCH")
    lifecycle=[evaluate_recovery_review(x,evaluated_at=evaluated_at) for x in reviews]
    payload={"policy_version":POLICY_VERSION,"reconciliation_fingerprint":reconciliation.get("reconciliation_fingerprint"),"lifecycle_count":len(lifecycle),"lifecycles":lifecycle,"human_governed":True,"automatic_recovery_performed":False,"decision_executed":False,"interpretation":"RECOVERY_REVIEW_LIFECYCLE","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None}
    return dict(payload,lifecycle_snapshot_fingerprint=fingerprint(payload))
