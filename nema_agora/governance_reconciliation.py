"""Phase 39 governance reconciliation."""
from __future__ import annotations
import hashlib, json
from typing import Any, Iterable, Mapping
from nema_agora.audit_ledger import AuditLedger

POLICY_VERSION = "phase39-v1"
TRACEABLE = "TRACEABLE"
CONTROL_REQUIRED = "CONTROL_REQUIRED"
DECISION_KINDS = {
    "evaluation_completed": ("EVALUATION_COMPLETED", "evaluation", "run_id"),
    "review_decision": ("REVIEW_DECISION_RECORDED", "review", "review_id"),
    "lifecycle_decision": ("MODEL_LIFECYCLE_DECIDED", "model_governance", "decision_id"),
}
REVIEW_MAP = {"CONFIRMED_USEFUL":"APPROVE","UNSAFE":"REJECT","NEEDS_CORRECTION":"HUMAN_REVIEW_REQUIRED","NOT_APPLICABLE":"DEFER"}
LIFECYCLE_MAP = {"RETAIN":"APPROVE","SUSPEND":"REJECT","REVIEW":"DEFER","RE_ADMIT_REQUIRED":"DEFER"}

def _fp(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",",":"), ensure_ascii=False, default=str).encode()).hexdigest()

def _source(kind: str, row: Mapping[str, Any]) -> dict[str, Any]:
    if kind not in DECISION_KINDS: raise ValueError("Unsupported decision kind.")
    event_type, module, id_key = DECISION_KINDS[kind]
    artifact_id = str(row.get(id_key, "")).strip()
    if not artifact_id: raise ValueError(f"{id_key} is required.")
    if kind == "review_decision":
        decision = REVIEW_MAP.get(str(row.get("decision", ""))); actor = str(row.get("reviewer_id", "")).strip()
    elif kind == "lifecycle_decision":
        decision = LIFECYCLE_MAP.get(str(row.get("action", ""))); actor = str(row.get("decided_by", "")).strip()
    else:
        decision = "HUMAN_REVIEW_REQUIRED"; actor = str(row.get("actor_id", "")).strip()
    if decision is None: raise ValueError("Unsupported source decision code.")
    return {"decision_kind":kind,"event_type":event_type,"source_module":module,"artifact_id":artifact_id,"status":"COMPLETED","decision":decision,"actor_id":actor}

def reconcile_decisions(source_records: Mapping[str, Iterable[Mapping[str, Any]]], audit_entries: Iterable[Mapping[str, Any]], *, ledger_verification: Mapping[str, Any] | None = None) -> dict[str, Any]:
    exceptions=[]; sources=[]
    for kind, rows in source_records.items():
        try:
            for row in rows: sources.append(_source(kind,row))
        except (TypeError, ValueError) as exc:
            exceptions.append({"code":"SOURCE_RECORD_INVALID","severity":"CRITICAL","decision_kind":kind,"artifact_id":None,"detail":str(exc)})
    audits=[]
    valid_types={spec[0] for spec in DECISION_KINDS.values()}
    for entry in audit_entries:
        if entry.get("event_type") != "GOVERNED_AUDIT_EVENT": continue
        payload=entry.get("payload") or {}; meta=payload.get("metadata") if isinstance(payload,dict) else None
        meta=meta if isinstance(meta,dict) else {}
        event_type=meta.get("event_type") or payload.get("event_type")
        if event_type not in valid_types: continue
        kind=next(k for k,v in DECISION_KINDS.items() if v[0]==event_type)
        audits.append({"decision_kind":kind,"event_type":event_type,"artifact_id":str(meta.get("artifact_id","")).strip(),"status":meta.get("status"),"decision":meta.get("decision"),"actor_id":str(entry.get("actor_id","")).strip(),"source_module":meta.get("source_module"),"entry_id":entry.get("entry_id")})
    si={}; ai={}
    for x in sources: si.setdefault((x["decision_kind"],x["artifact_id"]),[]).append(x)
    for x in audits: ai.setdefault((x["decision_kind"],x["artifact_id"]),[]).append(x)
    matched=0
    def add(code,kind,artifact,detail): exceptions.append({"code":code,"severity":"CRITICAL","decision_kind":kind,"artifact_id":artifact,"detail":detail})
    for key, rows in si.items():
        kind, artifact=key; ar=ai.get(key,[])
        if len(rows)>1: add("DUPLICATE_SOURCE_DECISION",kind,artifact,"Multiple authoritative records share one decision boundary.")
        if not ar: add("MISSING_AUDIT_EVENT",kind,artifact,"Authoritative decision has no governed audit event."); continue
        if len(ar)>1: add("AMBIGUOUS_AUDIT_COVERAGE",kind,artifact,"More than one governed audit event covers one decision boundary."); continue
        src,a=rows[0],ar[0]
        if src["actor_id"] and src["actor_id"]!=a["actor_id"]: add("ACTOR_MISMATCH",kind,artifact,"Audit actor differs from authoritative actor.")
        if src["status"]!=a["status"] or src["decision"]!=a["decision"]: add("DECISION_METADATA_MISMATCH",kind,artifact,"Audit status or decision differs from authoritative record.")
        if src["source_module"]!=a["source_module"]: add("SOURCE_MODULE_MISMATCH",kind,artifact,"Audit source module differs from authoritative store.")
        if not any(e["decision_kind"]==kind and e["artifact_id"]==artifact for e in exceptions): matched+=1
    for key in ai:
        if key not in si: add("ORPHAN_AUDIT_EVENT",key[0],key[1],"Governed audit event has no authoritative source decision.")
    if ledger_verification is not None and not ledger_verification.get("valid"): add("INVALID_LEDGER",None,None,"Audit ledger verification failed; reconciliation cannot be trusted.")
    exceptions=sorted(exceptions,key=lambda e:(e["code"],e["decision_kind"] or "",e["artifact_id"] or ""))
    status=TRACEABLE if not exceptions else CONTROL_REQUIRED
    material={"policy_version":POLICY_VERSION,"status":status,"matched":matched,"source_count":len(sources),"audit_count":len(audits),"exceptions":exceptions}
    digest=_fp(material)
    return {**material,"reconciliation_id":"REC-"+digest[:16].upper(),"reconciliation_fingerprint":digest,"notice":"Detection only: no historical audit event is silently repaired, deleted, or rewritten."}

def reconcile_database(database_path: str, *, limit: int = 500) -> dict[str, Any]:
    from nema_agora.lab import EvaluationRunStore
    from nema_agora.review_governance import ReviewStore
    evaluation=EvaluationRunStore(database_path).list(limit=min(max(int(limit),1),100))
    reviews=ReviewStore(database_path).list_reviews(limit=min(max(int(limit),1),500))
    lifecycle=ReviewStore(database_path).list_lifecycle_decisions(limit=min(max(int(limit),1),200))
    ledger=AuditLedger(database_path); verification=ledger.verify()
    entries=ledger.list_entries(limit=5000) if verification.get("entries",0)<=5000 else []
    return reconcile_decisions({"evaluation_completed":evaluation,"review_decision":reviews,"lifecycle_decision":lifecycle},entries,ledger_verification=verification)
