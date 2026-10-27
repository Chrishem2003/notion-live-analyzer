"""Phase 51 — deterministic preparation package for an authorized governance review."""
from __future__ import annotations
import hashlib,json
from typing import Any,Mapping

POLICY_VERSION="phase51-v1"

def fingerprint(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()

def prepare_review_decision(*,workspace:Mapping[str,Any],current_snapshot:Mapping[str,Any],
                            reviewer_actor_id:str)->dict[str,Any]:
    if not str(reviewer_actor_id).strip():
        raise ValueError("reviewer_actor_id is required")
    case=workspace.get("case")
    if not case:
        return {"policy_version":POLICY_VERSION,"state":"NOT_READY","reason":"NO_CASE"}
    if workspace.get("state")!="READY_FOR_HUMAN_REVIEW":
        return {"policy_version":POLICY_VERSION,"state":"NOT_READY","reason":"WORKSPACE_NOT_READY"}
    if not case.get("required_action")=="HUMAN_REVIEW_REQUIRED":
        return {"policy_version":POLICY_VERSION,"state":"NOT_READY","reason":"HUMAN_REVIEW_REQUIRED"}
    package={"case_id":case.get("case_id"),"queue_context":case.get("queue_context"),
        "finding":case.get("finding"),"accountable_artifacts":case.get("queue_context",{}).get("accountable_artifacts",{}),
        "attestations":case.get("attestations",[]),"lifecycle_items":case.get("lifecycle_items",[]),
        "lifecycle_decisions":case.get("lifecycle_decisions",[]),"provenance_bindings":case.get("provenance_bindings",[]),
        "current_snapshot":dict(current_snapshot),"prepared_by":str(reviewer_actor_id).strip(),
        "decision_status":"NOT_DECIDED"}
    return {"policy_version":POLICY_VERSION,"state":"READY_FOR_HUMAN_DECISION",
            "decision_status":"NOT_DECIDED","package":package,
            "package_fingerprint":fingerprint(package),
            "notice":"Preparation only. No governance decision is executed, recorded, approved or inferred by this layer."}
