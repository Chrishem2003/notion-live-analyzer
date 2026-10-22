"""Phase 47 — cross-layer governance evidence reconciliation."""
from __future__ import annotations
import hashlib,json
from typing import Any,Iterable,Mapping
POLICY_VERSION="phase47-v1"
def fingerprint(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def reconcile(*,attestations:Iterable[Mapping[str,Any]],lifecycle_items:Iterable[Mapping[str,Any]],
              bindings:Iterable[Mapping[str,Any]],provenance_result:Mapping[str,Any],
              current_snapshot:Mapping[str,Any])->dict[str,Any]:
    atts={str(x.get("attestation_id")):x for x in attestations if x.get("attestation_id")}
    items={str(x.get("attestation_id")):x for x in lifecycle_items if x.get("attestation_id")}
    binds=list(bindings); findings=[]
    snap={k:str(current_snapshot.get(k,"")) for k in ("reconciliation_fingerprint","evidence_registry_fingerprint","provenance_fingerprint")}
    for aid in atts:
        if aid not in items: findings.append({"code":"ORPHAN_ATTESTATION","attestation_id":aid})
    for aid,row in items.items():
        if aid not in atts: findings.append({"code":"ORPHAN_LIFECYCLE","attestation_id":aid})
        decision=row.get("latest_decision")
        if decision and str(decision.get("attestation_id"))!=aid: findings.append({"code":"LIFECYCLE_IDENTITY_MISMATCH","attestation_id":aid})
    seen_decisions=set(); seen_att_bindings=set()
    for b in binds:
        aid=str(b.get("attestation_id","")); did=str(b.get("decision_id",""))
        if did in seen_decisions: findings.append({"code":"DUPLICATE_DECISION_BINDING","decision_id":did,"binding_id":b.get("binding_id")})
        seen_decisions.add(did)
        if aid not in atts: findings.append({"code":"ORPHAN_PROVENANCE_BINDING","attestation_id":aid,"binding_id":b.get("binding_id")})
        if aid in seen_att_bindings: findings.append({"code":"DUPLICATE_ATTESTATION_BINDING","attestation_id":aid})
        seen_att_bindings.add(aid)
        for k,v in snap.items():
            if str(b.get(k,""))!=v: findings.append({"code":"PROVENANCE_SNAPSHOT_MISMATCH","field":k,"binding_id":b.get("binding_id")})
    for failure in provenance_result.get("failures",[]): findings.append({"code":"PROVENANCE_VALIDATION_FAILURE","detail":failure})
    bound_ids={str(b.get("attestation_id")) for b in binds}
    for aid,row in items.items():
        if row.get("lifecycle_state")=="ACTIVE" and aid not in bound_ids: findings.append({"code":"ACTIVE_WITHOUT_PROVENANCE_BINDING","attestation_id":aid})
    canonical=sorted(findings,key=lambda x:json.dumps(x,sort_keys=True))
    return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED" if canonical else "RECONCILED",
            "finding_count":len(canonical),"findings":canonical,
            "reconciliation_fingerprint":fingerprint({"snapshot":snap,"findings":canonical})}
