"""Phase 42 — closure evidence registry, provenance binding, and reconciliation reporting.

Closure evidence is append-only metadata. It can support a Phase 41 closure decision,
but registration never closes an exception by itself. Evidence must be explicitly
verified, bound to the current reconciliation fingerprint and the exact exception
and resolution event before it can be used by the closure evaluator.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json, re, sqlite3
from typing import Any, Mapping
from nema_agora.governance_exception_closure import CLOSED, CONTROL_REQUIRED, REVIEW_REQUIRED, evaluate_closure, reconcile_and_evaluate

POLICY_VERSION = "phase42-v1"
VERIFICATION_STATES = frozenset({"REGISTERED", "VERIFIED", "REJECTED", "STALE"})
EVIDENCE_TYPES = frozenset({"SOURCE_CORRECTION","DUPLICATE_CONFIRMATION","FALSE_POSITIVE_REVIEW","AUDIT_RECONCILIATION","OTHER_GOVERNANCE_EVIDENCE"})
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode("utf-8")).hexdigest()

def _safe(value: str, label: str) -> str:
    value=str(value).strip()
    if not value or not _SAFE_ID.fullmatch(value): raise ValueError(f"{label} must be a stable non-identifying ID.")
    return value

class ClosureEvidenceRegistry:
    """Append-only SQLite registry for evidence that may support exception closure."""
    def __init__(self,database_path:str):
        self.database_path=str(database_path)
        if not self.database_path.strip(): raise ValueError("Explicit database path required.")
        with sqlite3.connect(self.database_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS closure_evidence (
                evidence_id TEXT PRIMARY KEY, evidence_hash TEXT NOT NULL, evidence_type TEXT NOT NULL,
                reconciliation_fingerprint TEXT NOT NULL, exception_code TEXT NOT NULL, decision_kind TEXT NOT NULL,
                artifact_id TEXT NOT NULL, resolution_event_id TEXT NOT NULL, provenance_ref TEXT NOT NULL,
                verification_state TEXT NOT NULL, registered_by TEXT NOT NULL, registered_at TEXT NOT NULL,
                policy_version TEXT NOT NULL)""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS closure_evidence_no_update
                BEFORE UPDATE ON closure_evidence BEGIN SELECT RAISE(ABORT,'closure evidence registry is append-only'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS closure_evidence_no_delete
                BEFORE DELETE ON closure_evidence BEGIN SELECT RAISE(ABORT,'closure evidence registry is append-only'); END""")
    def register(self,*,evidence_id:str,evidence_hash:str,evidence_type:str,reconciliation_fingerprint:str,
                 exception_code:str,decision_kind:str,artifact_id:str,resolution_event_id:str,
                 provenance_ref:str,registered_by:str,verification_state:str="REGISTERED")->dict[str,Any]:
        evidence_id=_safe(evidence_id,"evidence_id"); reconciliation_fingerprint=_safe(reconciliation_fingerprint,"reconciliation_fingerprint")
        exception_code=_safe(exception_code,"exception_code"); decision_kind=_safe(decision_kind,"decision_kind")
        artifact_id=_safe(artifact_id,"artifact_id"); resolution_event_id=_safe(resolution_event_id,"resolution_event_id")
        provenance_ref=_safe(provenance_ref,"provenance_ref"); registered_by=_safe(registered_by,"registered_by")
        evidence_hash=str(evidence_hash).strip().lower()
        if not _SHA256.fullmatch(evidence_hash): raise ValueError("evidence_hash must be a lowercase SHA-256 hash.")
        if evidence_type not in EVIDENCE_TYPES: raise ValueError("Unsupported evidence_type.")
        if verification_state not in VERIFICATION_STATES: raise ValueError("Unsupported verification_state.")
        row={"evidence_id":evidence_id,"evidence_hash":evidence_hash,"evidence_type":evidence_type,
             "reconciliation_fingerprint":reconciliation_fingerprint,"exception_code":exception_code,
             "decision_kind":decision_kind,"artifact_id":artifact_id,"resolution_event_id":resolution_event_id,
             "provenance_ref":provenance_ref,"verification_state":verification_state,"registered_by":registered_by,
             "registered_at":datetime.now(timezone.utc).isoformat(),"policy_version":POLICY_VERSION}
        with sqlite3.connect(self.database_path) as db:
            try: db.execute("""INSERT INTO closure_evidence
                (evidence_id,evidence_hash,evidence_type,reconciliation_fingerprint,exception_code,decision_kind,
                 artifact_id,resolution_event_id,provenance_ref,verification_state,registered_by,registered_at,policy_version)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",tuple(row.values()))
            except sqlite3.IntegrityError as exc: raise ValueError("EVIDENCE_ID_CONFLICT: evidence IDs are immutable and cannot be overwritten.") from exc
        return row
    def list(self,*,limit:int=500)->list[dict[str,Any]]:
        safe_limit=max(1,min(int(limit),5000))
        with sqlite3.connect(self.database_path) as db:
            db.row_factory=sqlite3.Row
            rows=db.execute("SELECT * FROM closure_evidence ORDER BY registered_at DESC, evidence_id DESC LIMIT ?",(safe_limit,)).fetchall()
        return [dict(row) for row in rows]

def _payload(resolution):
    payload=resolution.get("payload") if isinstance(resolution,Mapping) else None
    if isinstance(payload,Mapping):
        payload=payload.get("metadata",payload)
        if isinstance(payload,Mapping) and isinstance(payload.get("metadata"),Mapping): payload=payload["metadata"]
    return payload if isinstance(payload,Mapping) else None

def _event_id(resolution):
    return str((resolution or {}).get("entry_id") or (resolution or {}).get("event_id") or "").strip() or None

def evaluate_with_registry(reconciliation:Mapping[str,Any],resolutions:list[Mapping[str,Any]],evidence_rows:list[Mapping[str,Any]])->dict[str,Any]:
    fp=str(reconciliation.get("reconciliation_fingerprint","")).strip()
    current={}
    for r in resolutions:
        p=_payload(r)
        if p and p.get("resolution_status")=="RESOLVED" and str(p.get("reconciliation_fingerprint","")).strip()==fp:
            current[(p.get("exception_code"),p.get("decision_kind"),p.get("artifact_id"))]=r
    usable={}; provenance={}
    for exc in reconciliation.get("exceptions") or []:
        if not isinstance(exc,Mapping): continue
        key=(exc.get("code",exc.get("exception_code")),exc.get("decision_kind"),exc.get("artifact_id"))
        resolution=current.get(key); expected=_event_id(resolution)
        candidates=[e for e in evidence_rows if e.get("verification_state")=="VERIFIED"
                    and e.get("reconciliation_fingerprint")==fp
                    and (e.get("exception_code"),e.get("decision_kind"),e.get("artifact_id"))==key
                    and (expected is None or e.get("resolution_event_id")==expected)
                    and _SHA256.fullmatch(str(e.get("evidence_hash","")).lower())]
        if candidates:
            candidates.sort(key=lambda e:(str(e.get("registered_at","")),str(e.get("evidence_id",""))))
            e=candidates[-1]; usable[key]={"evidence_id":e["evidence_id"],"evidence_hash":e["evidence_hash"]}
            provenance[key]={"evidence_id":e["evidence_id"],"evidence_type":e["evidence_type"],"provenance_ref":e["provenance_ref"],"resolution_event_id":e["resolution_event_id"],"verification_state":e["verification_state"]}
    result=evaluate_closure(reconciliation,resolutions,evidence_by_key=usable)
    for item in result["results"]:
        key=(item["exception_code"],item["decision_kind"],item["artifact_id"]); item["evidence_provenance"]=provenance.get(key)
    result["policy_version"]=POLICY_VERSION
    result["provenance_chain"]="Observation → Review Decision → Audit Event → Reconciliation Exception → Human Resolution → Closure Evidence → Derived Closure State"
    return result

def build_operational_report(closure_result:Mapping[str,Any],*,evidence_rows:list[Mapping[str,Any]],resolutions:list[Mapping[str,Any]])->dict[str,Any]:
    results=list(closure_result.get("results") or []); fp=str(closure_result.get("reconciliation_fingerprint","")).strip()
    stale=sum(1 for r in resolutions if (_payload(r) or {}).get("resolution_status")=="RESOLVED" and str((_payload(r) or {}).get("reconciliation_fingerprint","")).strip()!=fp)
    return {"policy_version":POLICY_VERSION,"reconciliation_fingerprint":fp,"total_exceptions":len(results),
            "open":sum(r.get("closure_code")=="NO_RESOLUTION" for r in results),
            "review_required":sum(r.get("status")==REVIEW_REQUIRED for r in results),
            "control_required":sum(r.get("status")==CONTROL_REQUIRED for r in results),
            "closed":sum(r.get("status")==CLOSED for r in results),"stale_resolutions":stale,
            "missing_evidence":sum(r.get("closure_code")=="MISSING_CLOSURE_EVIDENCE" for r in results),
            "unresolved_critical":sum(r.get("severity")=="CRITICAL" and r.get("status")!=CLOSED for r in results),
            "registered_evidence":len(evidence_rows),"verified_evidence":sum(e.get("verification_state")=="VERIFIED" for e in evidence_rows),
            "decision_notice":"Operational reconciliation is derived evidence for human governance. It never mutates source records or historical audit events."}

def reconcile_with_evidence(database_path:str,*,limit:int=500)->dict[str,Any]:
    base=reconcile_and_evaluate(database_path,limit=limit)
    from nema_agora.governance_exception_resolution import GovernanceExceptionResolver
    resolutions=GovernanceExceptionResolver(database_path).list_resolutions(limit=500)
    evidence=ClosureEvidenceRegistry(database_path).list(limit=5000)
    reconciliation={"reconciliation_fingerprint":base.get("reconciliation_fingerprint"),"exceptions":[{"code":x.get("exception_code"),"severity":x.get("severity"),"decision_kind":x.get("decision_kind"),"artifact_id":x.get("artifact_id"),"detail":x.get("detail")} for x in base.get("results",[])]}
    closure=evaluate_with_registry(reconciliation,resolutions,evidence)
    return {"closure":closure,"report":build_operational_report(closure,evidence_rows=evidence,resolutions=resolutions),"evidence":evidence}
