"""Phase 48 — Governance Evidence Casebook.
Builds deterministic, read-only case records from Phase 47 findings.
"""
from __future__ import annotations
import hashlib,json
from typing import Any,Iterable,Mapping
POLICY_VERSION="phase48-v1"
def fingerprint(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def build_casebook(*,reconciliation_result:Mapping[str,Any],attestations:Iterable[Mapping[str,Any]],lifecycle_items:Iterable[Mapping[str,Any]],lifecycle_decisions:Iterable[Mapping[str,Any]],bindings:Iterable[Mapping[str,Any]],current_snapshot:Mapping[str,Any])->dict[str,Any]:
    atts=list(attestations); items=list(lifecycle_items); decisions=list(lifecycle_decisions); binds=list(bindings)
    findings=list(reconciliation_result.get("findings",[])); cases=[]
    for finding in findings:
        aid=str(finding.get("attestation_id","")).strip(); did=str(finding.get("decision_id","")).strip(); bid=str(finding.get("binding_id","")).strip()
        related_att=[x for x in atts if not aid or str(x.get("attestation_id"))==aid]
        related_item=[x for x in items if not aid or str(x.get("attestation_id"))==aid]
        related_dec=[x for x in decisions if (did and str(x.get("decision_id"))==did) or (aid and str(x.get("attestation_id"))==aid)]
        related_bind=[x for x in binds if (bid and str(x.get("binding_id"))==bid) or (aid and str(x.get("attestation_id"))==aid)]
        payload={"finding":finding,"attestations":related_att,"lifecycle_items":related_item,"lifecycle_decisions":related_dec,"provenance_bindings":related_bind,"current_snapshot":dict(current_snapshot)}
        case_id="CASE-"+fingerprint(payload)[:24].upper()
        cases.append({"case_id":case_id,"code":finding.get("code"),"severity":finding.get("severity","CONTROL_REQUIRED"),"required_action":"HUMAN_REVIEW_REQUIRED","accountable_artifacts":{"attestation_ids":sorted({str(x.get("attestation_id")) for x in related_att if x.get("attestation_id")}),"decision_ids":sorted({str(x.get("decision_id")) for x in related_dec if x.get("decision_id")}),"binding_ids":sorted({str(x.get("binding_id")) for x in related_bind if x.get("binding_id")})},"finding":finding,"evidence":payload})
    cases=sorted(cases,key=lambda x:(str(x["code"]),str(x["case_id"])))
    return {"policy_version":POLICY_VERSION,"overall_state":"CONTROL_REQUIRED" if findings else "NO_CASES","finding_count":len(findings),"case_count":len(cases),"cases":cases,"casebook_fingerprint":fingerprint({"snapshot":dict(current_snapshot),"cases":cases}),"notice":"Casebook output is read-only governance evidence. It does not establish environmental truth, NEMA authorization, regulatory status, production approval, enforcement, emergency response, or autonomous authority."}
