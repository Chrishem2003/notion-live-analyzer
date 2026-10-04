"""Phase 49 — deterministic, read-only governance review queue."""
from __future__ import annotations
import hashlib,json
from typing import Any,Iterable,Mapping
POLICY_VERSION="phase49-v1"
_RANK={"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3,"CONTROL_REQUIRED":0}
def fingerprint(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def _priority(case:Mapping[str,Any])->tuple:
    severity=str(case.get("severity","CONTROL_REQUIRED")).upper()
    finding=case.get("finding") or {}
    age=int(finding.get("age_days",0) or 0)
    unresolved=1 if str(case.get("required_action"))=="HUMAN_REVIEW_REQUIRED" else 0
    dependency=1 if finding.get("dependency") else 0
    return (_RANK.get(severity,4),-unresolved,-min(age,365),-dependency,str(case.get("case_id","")))
def build_review_queue(*,cases:Iterable[Mapping[str,Any]],current_snapshot:Mapping[str,Any])->dict[str,Any]:
    rows=[]
    for case in cases:
        c=dict(case)
        finding=dict(c.get("finding") or {})
        severity=str(c.get("severity","CONTROL_REQUIRED")).upper()
        age=int(finding.get("age_days",0) or 0)
        rows.append({"case_id":c.get("case_id"),"code":c.get("code"),"severity":severity,
                     "age_days":max(0,age),"dependency":bool(finding.get("dependency")),
                     "review_state":"HUMAN_REVIEW_REQUIRED" if c.get("required_action")=="HUMAN_REVIEW_REQUIRED" else "INFORMATIONAL",
                     "accountable_artifacts":c.get("accountable_artifacts",{}),
                     "finding":finding})
    rows=sorted(rows,key=_priority)
    for i,row in enumerate(rows,1): row["queue_position"]=i
    return {"policy_version":POLICY_VERSION,"overall_state":"REVIEW_REQUIRED" if rows else "EMPTY",
            "queue_count":len(rows),"queue":rows,
            "current_snapshot":dict(current_snapshot),
            "queue_fingerprint":fingerprint({"snapshot":dict(current_snapshot),"queue":rows}),
            "notice":"This queue is a deterministic prioritization aid for authorized human review. It does not change governance state, establish environmental truth, authorize NEMA action, enforcement, emergency response, production or autonomous decisions."}
