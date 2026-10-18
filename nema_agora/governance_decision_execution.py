"""Phase 52 — explicit, human-governed decision execution boundary."""
from __future__ import annotations
import hashlib,json
from typing import Any,Mapping

POLICY_VERSION="phase52-v1"
_ALLOWED={"APPROVE","REJECT","REVOKE","SUPERSEDE"}

def fingerprint(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()

def validate_execution_request(*,prepared_package:Mapping[str,Any],decision:str,
                                actor_id:str,role:str,current_snapshot:Mapping[str,Any])->dict[str,Any]:
    decision=str(decision).strip().upper()
    actor_id=str(actor_id).strip()
    role=str(role).strip().lower()
    package_snapshot=prepared_package.get("current_snapshot") or {}
    failures=[]
    if prepared_package.get("decision_status")!="NOT_DECIDED": failures.append("PACKAGE_ALREADY_DECIDED")
    if decision not in _ALLOWED: failures.append("UNSUPPORTED_DECISION")
    if not actor_id: failures.append("ACTOR_REQUIRED")
    if role not in {"coordinator","admin"}: failures.append("AUTHORIZED_DECISION_ROLE_REQUIRED")
    if package_snapshot!=dict(current_snapshot): failures.append("CURRENT_SNAPSHOT_MISMATCH")
    if prepared_package.get("case_id") is None: failures.append("CASE_REQUIRED")
    state="READY_FOR_HUMAN_EXECUTION" if not failures else "CONTROL_REQUIRED"
    return {"policy_version":POLICY_VERSION,"state":state,"decision":decision,
            "actor_id":actor_id,"role":role,"failures":failures,
            "execution_authorized":False,
            "execution_action":"USE_EXISTING_HUMAN_GOVERNED_LIFECYCLE_WORKFLOW",
            "request_fingerprint":fingerprint({"package":dict(prepared_package),"decision":decision,
                "actor_id":actor_id,"role":role,"current_snapshot":dict(current_snapshot)}),
            "notice":"This boundary validates prerequisites only. It never writes a lifecycle decision, approves/rejects an attestation, changes workflow state, or performs autonomous governance action."}
