"""Phase 50 — authenticated, read-only governance review workspace."""
from __future__ import annotations
import hashlib,json
from typing import Any,Iterable,Mapping

POLICY_VERSION="phase50-v1"

def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()

def build_workspace(*,queue_result:Mapping[str,Any],casebook:Mapping[str,Any],
                    attestations:Iterable[Mapping[str,Any]],lifecycle_items:Iterable[Mapping[str,Any]],
                    lifecycle_decisions:Iterable[Mapping[str,Any]],bindings:Iterable[Mapping[str,Any]],
                    provenance_result:Mapping[str,Any],current_snapshot:Mapping[str,Any],
                    case_id:str|None=None)->dict[str,Any]:
    cases={str(x.get("case_id")):x for x in casebook.get("cases",[]) if x.get("case_id")}
    queue={str(x.get("case_id")):x for x in queue_result.get("queue",[]) if x.get("case_id")}
    selected=case_id or (next(iter(queue)) if queue else next(iter(cases),None))
    if selected is None:
        return {"policy_version":POLICY_VERSION,"state":"EMPTY","case":None,"workspace_fingerprint":fingerprint({"snapshot":dict(current_snapshot),"case":None})}
    case=cases.get(str(selected))
    if not case:
        return {"policy_version":POLICY_VERSION,"state":"CASE_NOT_FOUND","case_id":str(selected),"case":None,"workspace_fingerprint":fingerprint({"snapshot":dict(current_snapshot),"case_id":str(selected),"missing":True})}
    aid=set(case.get("accountable_artifacts",{}).get("attestation_ids",[]))
    did=set(case.get("accountable_artifacts",{}).get("decision_ids",[]))
    bid=set(case.get("accountable_artifacts",{}).get("binding_ids",[]))
    atts=[dict(x) for x in attestations if str(x.get("attestation_id")) in aid]
    decisions=[dict(x) for x in lifecycle_decisions if str(x.get("decision_id")) in did or str(x.get("attestation_id")) in aid]
    items=[dict(x) for x in lifecycle_items if str(x.get("attestation_id")) in aid]
    binds=[dict(x) for x in bindings if str(x.get("binding_id")) in bid or str(x.get("attestation_id")) in aid]
    pstate={str(x.get("binding_id")):x.get("state") for x in provenance_result.get("bindings",[])}
    detail={"case_id":case["case_id"],"queue_context":queue.get(str(selected)),
            "finding":case.get("finding"),"required_action":"HUMAN_REVIEW_REQUIRED",
            "attestations":atts,"lifecycle_items":items,"lifecycle_decisions":decisions,
            "provenance_bindings":[{**x,"validation_state":pstate.get(str(x.get("binding_id")),"UNKNOWN")} for x in binds],
            "current_snapshot":dict(current_snapshot),
            "review_context":{"provenance_failures":provenance_result.get("failures",[]),
                              "governance_boundary":True}}
    return {"policy_version":POLICY_VERSION,"state":"READY_FOR_HUMAN_REVIEW","case":detail,
            "workspace_fingerprint":fingerprint(detail),
            "notice":"Read-only governance evidence workspace. Human review is required for governance decisions. This surface does not change workflow state, establish environmental truth, authorize NEMA integration, regulatory action, enforcement, emergency response, production approval or autonomous decisions."}
