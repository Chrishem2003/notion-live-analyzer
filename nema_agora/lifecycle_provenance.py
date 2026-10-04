"""Phase 45 — lifecycle provenance and decision accountability."""
from __future__ import annotations
import hashlib, json, re, sqlite3
from typing import Any, Iterable, Mapping

POLICY_VERSION="phase45-v1"
_SHA=re.compile(r"^[0-9a-f]{64}$")
_ID=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

def fingerprint(value: Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()

def validate_fingerprint(value: str, label: str)->str:
    value=str(value).strip()
    if not _SHA.fullmatch(value): raise ValueError(f"{label} must be a lowercase SHA-256 fingerprint.")
    return value

def validate_id(value: str, label: str)->str:
    value=str(value).strip()
    if not _ID.fullmatch(value): raise ValueError(f"{label} must be a stable non-identifying ID.")
    return value

class LifecycleProvenanceRegistry:
    """Append-only binding ledger for lifecycle decisions and exact snapshots."""
    def __init__(self,database_path:str):
        self.database_path=str(database_path)
        if not self.database_path.strip(): raise ValueError("Explicit database path required.")
        with sqlite3.connect(self.database_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS attestation_lifecycle_provenance (
                binding_id TEXT PRIMARY KEY, decision_id TEXT NOT NULL, attestation_id TEXT NOT NULL,
                attester_actor_id TEXT NOT NULL, reviewer_actor_id TEXT NOT NULL,
                reconciliation_fingerprint TEXT NOT NULL, evidence_registry_fingerprint TEXT NOT NULL,
                provenance_fingerprint TEXT NOT NULL, superseding_attestation_id TEXT,
                bound_at TEXT NOT NULL, policy_version TEXT NOT NULL)""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS lifecycle_provenance_no_update
                BEFORE UPDATE ON attestation_lifecycle_provenance BEGIN
                SELECT RAISE(ABORT,'lifecycle provenance ledger is append-only'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS lifecycle_provenance_no_delete
                BEFORE DELETE ON attestation_lifecycle_provenance BEGIN
                SELECT RAISE(ABORT,'lifecycle provenance ledger is append-only'); END""")

    def bind(self,*,decision_id:str,attestation_id:str,attester_actor_id:str,reviewer_actor_id:str,
             reconciliation_fingerprint:str,evidence_registry_fingerprint:str,provenance_fingerprint:str,
             bound_at:str,superseding_attestation_id:str|None=None)->dict[str,Any]:
        did=validate_id(decision_id,"decision_id"); aid=validate_id(attestation_id,"attestation_id")
        aa=validate_id(attester_actor_id,"attester_actor_id"); ra=validate_id(reviewer_actor_id,"reviewer_actor_id")
        if aa==ra: raise ValueError("SEPARATION_OF_DUTIES_REQUIRED")
        rf=validate_fingerprint(reconciliation_fingerprint,"reconciliation_fingerprint")
        ef=validate_fingerprint(evidence_registry_fingerprint,"evidence_registry_fingerprint")
        pf=validate_fingerprint(provenance_fingerprint,"provenance_fingerprint")
        if superseding_attestation_id is not None: validate_id(superseding_attestation_id,"superseding_attestation_id")
        if not str(bound_at).strip(): raise ValueError("bound_at is required.")
        row={"binding_id":"BIND-"+fingerprint({"decision_id":did,"attestation_id":aid,"attester":aa,"reviewer":ra,
            "reconciliation":rf,"evidence":ef,"provenance":pf,"superseding":superseding_attestation_id})[:24].upper(),
             "decision_id":did,"attestation_id":aid,"attester_actor_id":aa,"reviewer_actor_id":ra,
             "reconciliation_fingerprint":rf,"evidence_registry_fingerprint":ef,"provenance_fingerprint":pf,
             "superseding_attestation_id":superseding_attestation_id,"bound_at":str(bound_at),
             "policy_version":POLICY_VERSION}
        with sqlite3.connect(self.database_path) as db:
            try: db.execute("INSERT INTO attestation_lifecycle_provenance VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",tuple(row.values()))
            except sqlite3.IntegrityError as exc: raise ValueError("PROVENANCE_BINDING_CONFLICT") from exc
        return row

    def list(self,limit:int=500)->list[dict[str,Any]]:
        with sqlite3.connect(self.database_path) as db:
            db.row_factory=sqlite3.Row
            return [dict(r) for r in db.execute("SELECT * FROM attestation_lifecycle_provenance ORDER BY bound_at DESC,binding_id DESC LIMIT ?",(max(1,min(int(limit),5000)),)).fetchall()]

def evaluate_provenance(bindings:Iterable[Mapping[str,Any]],decisions:Iterable[Mapping[str,Any]],attestations:Iterable[Mapping[str,Any]],*,
                        reconciliation_fingerprint:str,evidence_registry_fingerprint:str,provenance_fingerprint:str)->dict[str,Any]:
    decisions=list(decisions); atts={str(x.get("attestation_id")):x for x in attestations if x.get("attestation_id")}
    by_decision={str(x.get("decision_id")):x for x in decisions if x.get("decision_id")}
    results=[]; failures=[]
    for b in bindings:
        d=by_decision.get(str(b.get("decision_id"))); a=atts.get(str(b.get("attestation_id")))
        exact=(b.get("reconciliation_fingerprint")==reconciliation_fingerprint and
               b.get("evidence_registry_fingerprint")==evidence_registry_fingerprint and
               b.get("provenance_fingerprint")==provenance_fingerprint)
        identities=bool(d and a and d.get("attestation_id")==b.get("attestation_id") and
                        d.get("actor_id")==b.get("reviewer_actor_id") and
                        d.get("attester_actor_id")==b.get("attester_actor_id") and
                        d.get("actor_id")!=d.get("attester_actor_id"))
        state="VALID" if exact and identities else "STALE"
        if state!="VALID": failures.append({"binding_id":b.get("binding_id"),"reason":"SNAPSHOT_OR_IDENTITY_MISMATCH"})
        results.append({**dict(b),"state":state})
    return {"policy_version":POLICY_VERSION,"valid_count":sum(x["state"]=="VALID" for x in results),
            "stale_count":sum(x["state"]=="STALE" for x in results),"failure_count":len(failures),
            "failures":failures,"bindings":results,
            "current_snapshot":{"reconciliation_fingerprint":reconciliation_fingerprint,
            "evidence_registry_fingerprint":evidence_registry_fingerprint,"provenance_fingerprint":provenance_fingerprint}}

def validate_supersession_chain(bindings:Iterable[Mapping[str,Any]],attestations:Iterable[Mapping[str,Any]])->dict[str,Any]:
    ids={str(x.get("attestation_id")) for x in attestations if x.get("attestation_id")}
    failures=[]
    for b in bindings:
        target=b.get("superseding_attestation_id")
        if target and target not in ids: failures.append({"binding_id":b.get("binding_id"),"reason":"MISSING_SUPERSEDING_ATTESTATION","target":target})
        if target==b.get("attestation_id"): failures.append({"binding_id":b.get("binding_id"),"reason":"SELF_SUPERSESSION"})
    return {"valid":not failures,"failures":failures}
