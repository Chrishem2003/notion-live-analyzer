"""Phase 43 — governance evidence integrity, provenance completeness, and attestation.

Phase 43 verifies the current Phase 42 evidence bundle, derives a deterministic
integrity/provenance snapshot, and records explicit human attestations in an
append-only SQLite registry. Attestation is never inferred from evidence
presence and never changes source decisions or workflow state.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json, re, sqlite3
from typing import Any, Mapping, Iterable

POLICY_VERSION = "phase43-v1"
PENDING = "PENDING"
ATTESTED = "ATTESTED"
REJECTED = "REJECTED"
STALE = "STALE"
CONTROL_REQUIRED = "CONTROL_REQUIRED"
_ALLOWED_ATTEST_ROLES = frozenset({"coordinator", "admin"})
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_EVIDENCE_FIELDS = (
    "evidence_id","evidence_hash","evidence_type","reconciliation_fingerprint",
    "exception_code","decision_kind","artifact_id","resolution_event_id","provenance_ref",
)

def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",",":"), ensure_ascii=False, default=str).encode("utf-8")).hexdigest()

def _safe(value: Any, label: str) -> str:
    value = str(value).strip()
    if not value or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{label} must be a stable non-identifying ID.")
    return value

def _payload(row: Mapping[str, Any]) -> Mapping[str, Any]:
    p = row.get("payload")
    if isinstance(p, Mapping):
        p = p.get("metadata", p)
        if isinstance(p, Mapping) and isinstance(p.get("metadata"), Mapping):
            p = p["metadata"]
    return p if isinstance(p, Mapping) else {}

def _event_id(row: Mapping[str, Any]) -> str | None:
    return str(row.get("entry_id") or row.get("event_id") or "").strip() or None

def evidence_registry_fingerprint(rows: Iterable[Mapping[str, Any]]) -> str:
    canonical = []
    for row in rows:
        canonical.append({k: row.get(k) for k in _RECORD_FIELDS})
    canonical.sort(key=lambda x: (str(x["evidence_id"]), str(x["registered_at"])))
    return fingerprint(canonical)

_RECORD_FIELDS = (
    "evidence_id","evidence_hash","evidence_type","reconciliation_fingerprint",
    "exception_code","decision_kind","artifact_id","resolution_event_id",
    "provenance_ref","verification_state","registered_by","registered_at","policy_version",
)

def verify_evidence_integrity(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    errors: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        eid = str(row.get("evidence_id","")).strip()
        if not _SAFE_ID.fullmatch(eid):
            errors.append({"code":"INVALID_EVIDENCE_ID","evidence_id":eid})
        if eid in seen:
            errors.append({"code":"DUPLICATE_EVIDENCE_ID","evidence_id":eid})
        seen.add(eid)
        h = str(row.get("evidence_hash","")).strip()
        if not _SHA256.fullmatch(h) or h != h.lower():
            errors.append({"code":"INVALID_EVIDENCE_HASH","evidence_id":eid})
        for field in _REQUIRED_EVIDENCE_FIELDS:
            if not str(row.get(field,"")).strip():
                errors.append({"code":"MISSING_EVIDENCE_FIELD","field":field,"evidence_id":eid})
        if str(row.get("policy_version","")) != "phase42-v1":
            errors.append({"code":"UNEXPECTED_EVIDENCE_POLICY","evidence_id":eid})
        if str(row.get("verification_state","")) not in {"REGISTERED","VERIFIED","REJECTED","STALE"}:
            errors.append({"code":"INVALID_VERIFICATION_STATE","evidence_id":eid})
    fp = evidence_registry_fingerprint(rows)
    return {"policy_version":POLICY_VERSION,"valid":not errors,"row_count":len(rows),
            "error_count":len(errors),"errors":errors,"registry_fingerprint":fp}

def build_provenance_completeness(reconciliation: Mapping[str, Any],
                                  closure: Mapping[str, Any],
                                  resolutions: Iterable[Mapping[str, Any]],
                                  evidence_rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    fp = str(reconciliation.get("reconciliation_fingerprint","")).strip()
    resolution_map = {}
    for r in resolutions:
        p = _payload(r)
        if p.get("resolution_status") == "RESOLVED" and str(p.get("reconciliation_fingerprint","")).strip() == fp:
            key = (p.get("exception_code"),p.get("decision_kind"),p.get("artifact_id"))
            resolution_map[key] = r
    evidence_map = {}
    for e in evidence_rows:
        if e.get("verification_state") == "VERIFIED" and e.get("reconciliation_fingerprint") == fp:
            key = (e.get("exception_code"),e.get("decision_kind"),e.get("artifact_id"))
            evidence_map[key] = e
    items=[]
    for exc in reconciliation.get("exceptions") or []:
        key=(exc.get("code",exc.get("exception_code")),exc.get("decision_kind"),exc.get("artifact_id"))
        r=resolution_map.get(key); e=evidence_map.get(key)
        closure_item=next((x for x in closure.get("results",[]) if
            (x.get("exception_code"),x.get("decision_kind"),x.get("artifact_id"))==key),{})
        fields={
            "observation_reference": bool(exc.get("artifact_id")),
            "review_decision": bool(exc.get("decision_kind")),
            "audit_event": bool(_event_id(r)) if r else False,
            "reconciliation_fingerprint": bool(fp),
            "human_resolution": bool(r),
            "closure_evidence": bool(e and _SHA256.fullmatch(str(e.get("evidence_hash","")).lower() or "")),
            "derived_closure": bool(closure.get("closure_fingerprint")) and bool(closure_item),
        }
        missing=[k for k,v in fields.items() if not v]
        items.append({"exception_code":key[0],"decision_kind":key[1],"artifact_id":key[2],
                      "complete":not missing,"missing":missing,"fields":fields})
    complete=not items or all(x["complete"] for x in items)
    return {"policy_version":POLICY_VERSION,"reconciliation_fingerprint":fp,
            "complete":complete,"exception_count":len(items),
            "complete_count":sum(x["complete"] for x in items),"items":items}

class GovernanceAttestationRegistry:
    """Append-only human attestation records bound to exact integrity snapshots."""
    def __init__(self, database_path: str):
        self.database_path=str(database_path)
        if not self.database_path.strip(): raise ValueError("Explicit database path required.")
        with sqlite3.connect(self.database_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS governance_attestation (
                attestation_id TEXT PRIMARY KEY, attestation_state TEXT NOT NULL,
                actor_id TEXT NOT NULL, role TEXT NOT NULL, reconciliation_fingerprint TEXT NOT NULL,
                evidence_registry_fingerprint TEXT NOT NULL, provenance_fingerprint TEXT NOT NULL,
                reason TEXT NOT NULL, attested_at TEXT NOT NULL, policy_version TEXT NOT NULL)""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS governance_attestation_no_update
                BEFORE UPDATE ON governance_attestation BEGIN SELECT RAISE(ABORT,'governance attestation registry is append-only'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS governance_attestation_no_delete
                BEFORE DELETE ON governance_attestation BEGIN SELECT RAISE(ABORT,'governance attestation registry is append-only'); END""")
    def attest(self, *, actor_id: str, role: str, reconciliation_fingerprint: str,
               evidence_registry_fingerprint: str, provenance_fingerprint: str,
               reason: str, state: str = ATTESTED) -> dict[str, Any]:
        if role not in _ALLOWED_ATTEST_ROLES: raise PermissionError("Only coordinator or admin may attest governance integrity.")
        if state not in {ATTESTED,REJECTED}: raise ValueError("Human attestation state must be ATTESTED or REJECTED.")
        actor_id=_safe(actor_id,"actor_id"); reconciliation_fingerprint=_safe(reconciliation_fingerprint,"reconciliation_fingerprint")
        evidence_registry_fingerprint=_safe(evidence_registry_fingerprint,"evidence_registry_fingerprint")
        provenance_fingerprint=_safe(provenance_fingerprint,"provenance_fingerprint")
        reason=str(reason).strip()
        if len(reason)<3 or len(reason)>2000: raise ValueError("Attestation reason must contain 3-2000 characters.")
        aid="ATT-"+fingerprint({"actor_id":actor_id,"role":role,"reconciliation":reconciliation_fingerprint,
                                "evidence":evidence_registry_fingerprint,"provenance":provenance_fingerprint,
                                "state":state,"reason":reason})[:24].upper()
        row={"attestation_id":aid,"attestation_state":state,"actor_id":actor_id,"role":role,
             "reconciliation_fingerprint":reconciliation_fingerprint,"evidence_registry_fingerprint":evidence_registry_fingerprint,
             "provenance_fingerprint":provenance_fingerprint,"reason":reason,
             "attested_at":datetime.now(timezone.utc).isoformat(),"policy_version":POLICY_VERSION}
        with sqlite3.connect(self.database_path) as db:
            try:
                db.execute("""INSERT INTO governance_attestation VALUES (?,?,?,?,?,?,?,?,?,?)""",tuple(row.values()))
            except sqlite3.IntegrityError as exc:
                raise ValueError("ATTESTATION_ID_CONFLICT: identical attestation identity already exists.") from exc
        return row
    def list(self, limit: int = 500) -> list[dict[str, Any]]:
        safe=max(1,min(int(limit),5000))
        with sqlite3.connect(self.database_path) as db:
            db.row_factory=sqlite3.Row
            return [dict(r) for r in db.execute(
                "SELECT * FROM governance_attestation ORDER BY attested_at DESC, attestation_id DESC LIMIT ?",(safe,)).fetchall()]

def evaluate_attestations(attestations: Iterable[Mapping[str, Any]], *,
                          reconciliation_fingerprint: str, evidence_registry_fingerprint: str,
                          provenance_fingerprint: str, integrity_valid: bool,
                          provenance_complete: bool) -> list[dict[str, Any]]:
    out=[]
    for row in attestations:
        if row.get("attestation_state") not in {ATTESTED,REJECTED}: continue
        exact=(row.get("reconciliation_fingerprint")==reconciliation_fingerprint and
               row.get("evidence_registry_fingerprint")==evidence_registry_fingerprint and
               row.get("provenance_fingerprint")==provenance_fingerprint)
        state = row["attestation_state"] if exact and integrity_valid and provenance_complete else STALE
        out.append({**dict(row),"effective_state":state})
    return out

def build_integrity_snapshot(*, reconciliation: Mapping[str,Any], closure: Mapping[str,Any],
                             resolutions: Iterable[Mapping[str,Any]], evidence_rows: Iterable[Mapping[str,Any]],
                             attestations: Iterable[Mapping[str,Any]]) -> dict[str,Any]:
    evidence_rows=list(evidence_rows); resolutions=list(resolutions)
    integrity=verify_evidence_integrity(evidence_rows)
    provenance=build_provenance_completeness(reconciliation,closure,resolutions,evidence_rows)
    provenance_fp=fingerprint(provenance)
    current=evaluate_attestations(attestations,
        reconciliation_fingerprint=str(reconciliation.get("reconciliation_fingerprint","")),
        evidence_registry_fingerprint=integrity["registry_fingerprint"],
        provenance_fingerprint=provenance_fp,
        integrity_valid=integrity["valid"],provenance_complete=provenance["complete"])
    current_attested=[x for x in current if x["effective_state"]==ATTESTED]
    if not integrity["valid"] or not provenance["complete"]:
        overall=CONTROL_REQUIRED
    elif current_attested:
        overall=ATTESTED
    else:
        overall=PENDING
    return {"policy_version":POLICY_VERSION,"overall_state":overall,"integrity":integrity,
            "provenance":provenance,"provenance_fingerprint":provenance_fp,
            "attestations":current,
            "attestation_count":len(current),"active_attestation_count":len(current_attested),
            "notice":"Attestation is explicit human governance evidence. It never authorizes production, enforcement, emergency response, regulatory action, or environmental conclusions."}
