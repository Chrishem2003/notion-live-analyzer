"""Phase 54 — reconcile authoritative lifecycle decisions with evidentiary receipts."""
from __future__ import annotations
import hashlib,json
from typing import Any,Iterable,Mapping
POLICY_VERSION="phase54-v1"
def fingerprint(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def reconcile_decision_receipts(*,decisions:Iterable[Mapping[str,Any]],receipts:Iterable[Mapping[str,Any]],current_snapshot:Mapping[str,Any])->dict[str,Any]:
    ds=list(decisions); rs=list(receipts); dmap={str(x.get("decision_id")):x for x in ds if x.get("decision_id")}
    findings=[]; seen=set()
    for r in rs:
        rid=str(r.get("receipt_id","")); did=str(r.get("decision_id",""))
        if did in seen: findings.append({"code":"DUPLICATE_RECEIPT","decision_id":did,"receipt_id":rid})
        seen.add(did)
        if did not in dmap: findings.append({"code":"ORPHAN_RECEIPT","decision_id":did,"receipt_id":rid})
        payload=r.get("payload") or {}
        if str(payload.get("decision_id",""))!=did: findings.append({"code":"RECEIPT_IDENTITY_MISMATCH","receipt_id":rid})
        if payload.get("current_snapshot") is not None and dict(payload.get("current_snapshot") or {})!=dict(current_snapshot):
            findings.append({"code":"RECEIPT_SNAPSHOT_STALE","receipt_id":rid})
    for did in dmap:
        if did not in seen: findings.append({"code":"MISSING_RECEIPT","decision_id":did})
    canonical=sorted(findings,key=lambda x:json.dumps(x,sort_keys=True))
    return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED" if canonical else "RECONCILED",
            "finding_count":len(canonical),"findings":canonical,
            "reconciliation_fingerprint":fingerprint({"snapshot":dict(current_snapshot),"findings":canonical}),
            "notice":"Receipt reconciliation is evidence integrity only. The authoritative lifecycle ledger remains the source of governance decisions."}
