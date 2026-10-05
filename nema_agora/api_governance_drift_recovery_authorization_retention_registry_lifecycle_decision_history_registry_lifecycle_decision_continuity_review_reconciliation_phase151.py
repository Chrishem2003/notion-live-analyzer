"""Phase 151 — reconcile Phase 149 continuity monitors with Phase 150 human reviews."""
from __future__ import annotations
from collections import Counter
from typing import Any, Mapping, Sequence
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_monitor_phase149 import validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_phase150 import validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review
POLICY_VERSION="phase151-v1"

def reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_reviews(monitors: Sequence[Mapping[str,Any]], reviews: Sequence[Mapping[str,Any]], *, expected_review_count: int|None=None)->dict[str,Any]:
    if not isinstance(monitors,Sequence) or isinstance(monitors,(str,bytes)): raise ValueError("INVALID_MONITORS")
    if not isinstance(reviews,Sequence) or isinstance(reviews,(str,bytes)): raise ValueError("INVALID_REVIEWS")
    if expected_review_count is not None and (not isinstance(expected_review_count,int) or isinstance(expected_review_count,bool) or expected_review_count<0): raise ValueError("INVALID_EXPECTED_REVIEW_COUNT")
    findings=[]; valid_monitors=[]; valid_reviews=[]
    for i,x in enumerate(monitors):
        try: valid_monitors.append(validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(x))
        except ValueError as e: findings.append({"code":"INVALID_MONITOR","index":i,"reason":str(e)})
    for i,x in enumerate(reviews):
        try: valid_reviews.append(validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review(x))
        except ValueError as e: findings.append({"code":"INVALID_REVIEW","index":i,"reason":str(e)})
    for fp,n in Counter(x["monitor_fingerprint"] for x in valid_monitors).items():
        if n>1: findings.append({"code":"DUPLICATE_MONITOR_FINGERPRINT","identity":fp})
    for fp,n in Counter(x["review_fingerprint"] for x in valid_reviews).items():
        if n>1: findings.append({"code":"DUPLICATE_REVIEW_FINGERPRINT","identity":fp})
    monitor_map={x["monitor_fingerprint"]:x for x in valid_monitors}; bound={}
    for review in valid_reviews: bound.setdefault(review["monitor_fingerprint"],[]).append(review)
    allowed={"ACKNOWLEDGED":lambda s:s=="CONTINUITY_HEALTHY","REVIEW_CONTINUITY":lambda s:s=="NO_HISTORY","PRESERVE_AND_ESCALATE":lambda s:s=="CONTROL_REQUIRED","ESCALATED":lambda s:s in ("NO_HISTORY","CONTROL_REQUIRED")}
    for monitor in valid_monitors:
        fp=monitor["monitor_fingerprint"]; matches=bound.get(fp,[])
        if not matches: findings.append({"code":"UNREVIEWED_MONITOR","monitor_fingerprint":fp}); continue
        if len(matches)>1: findings.append({"code":"MULTIPLE_REVIEWS_FOR_MONITOR","monitor_fingerprint":fp,"count":len(matches)})
        for review in matches:
            if review["monitor_state"]!=monitor["state"]: findings.append({"code":"MONITOR_STATE_MISMATCH","monitor_fingerprint":fp})
            if review["monitor_recommendation"]!=monitor["recommendation"]: findings.append({"code":"RECOMMENDATION_MISMATCH","monitor_fingerprint":fp})
            if not allowed.get(review["outcome"],lambda _:False)(monitor["state"]): findings.append({"code":"OUTCOME_STATE_MISMATCH","monitor_fingerprint":fp,"outcome":review["outcome"]})
    for review in valid_reviews:
        if review["monitor_fingerprint"] not in monitor_map: findings.append({"code":"ORPHAN_REVIEW","monitor_fingerprint":review["monitor_fingerprint"]})
    if expected_review_count is not None and expected_review_count!=len(reviews): findings.append({"code":"REVIEW_COUNT_MISMATCH","expected":expected_review_count,"observed":len(reviews)})
    findings.sort(key=lambda x:(x.get("code",""),str(x.get("monitor_fingerprint","")),str(x.get("identity","")),str(x.get("index",""))))
    state="CONTROL_REQUIRED" if findings else ("RECONCILED" if valid_monitors else "NO_HISTORY")
    payload={"policy_version":POLICY_VERSION,"state":state,"monitor_count":len(monitors),"valid_monitor_count":len(valid_monitors),"review_count":len(reviews),"valid_review_count":len(valid_reviews),"expected_review_count":expected_review_count,"findings":findings,"read_only":True,"human_governed":True,"execution_gate_closed":True,"execution_permitted":False,"execution_performed":False,"automatic_repair_performed":False,"interpretation":"AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY_LIFECYCLE_DECISION_CONTINUITY_HUMAN_REVIEW_RECONCILIATION","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None,"emergency_action":None}
    return dict(payload,reconciliation_fingerprint=fingerprint(payload))

def validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_reconciliation(result: Mapping[str,Any])->dict[str,Any]:
    if not isinstance(result,Mapping): raise ValueError("INVALID_RECONCILIATION")
    required=("policy_version","state","monitor_count","valid_monitor_count","review_count","valid_review_count","expected_review_count","findings","read_only","human_governed","execution_gate_closed","execution_permitted","execution_performed","automatic_repair_performed","reconciliation_fingerprint")
    for k in required:
        if k not in result: raise ValueError("RECONCILIATION_FIELDS_REQUIRED")
    payload=dict(result); supplied=payload.pop("reconciliation_fingerprint")
    if fingerprint(payload)!=supplied: raise ValueError("RECONCILIATION_FINGERPRINT_MISMATCH")
    if result["policy_version"]!=POLICY_VERSION or result["state"] not in ("NO_HISTORY","RECONCILED","CONTROL_REQUIRED"): raise ValueError("INVALID_RECONCILIATION_POLICY_OR_STATE")
    if result["read_only"] is not True or result["human_governed"] is not True: raise ValueError("INVALID_GOVERNANCE_CONTROLS")
    if result["execution_gate_closed"] is not True or result["execution_permitted"] is not False or result["execution_performed"] is not False: raise ValueError("EXECUTION_GATE_VIOLATION")
    if result["automatic_repair_performed"] is not False: raise ValueError("AUTOMATIC_REPAIR_FORBIDDEN")
    return dict(result)
