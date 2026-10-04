"""Phase 40 — controlled governance exception resolution.

Exceptions are resolved by appending a new, immutable resolution event.
Historical source decisions and prior audit events are never rewritten.
"""
from __future__ import annotations
import hashlib, json
from typing import Any, Mapping
from nema_agora.audit_ledger import AuditLedger
from nema_agora.audit_events import AuditEventCapture

POLICY_VERSION = "phase40-v1"
RESOLUTION_EVENT = "GOVERNANCE_EXCEPTION_RESOLVED"
OPEN = "OPEN"
RESOLVED = "RESOLVED"
REOPENED = "REOPENED"
ALLOWED_CODES = {
    "SOURCE_RECORD_INVALID","MISSING_AUDIT_EVENT","ORPHAN_AUDIT_EVENT",
    "DUPLICATE_SOURCE_DECISION","AMBIGUOUS_AUDIT_COVERAGE","ACTOR_MISMATCH",
    "DECISION_METADATA_MISMATCH","SOURCE_MODULE_MISMATCH","INVALID_LEDGER",
}
ALLOWED_OUTCOMES = {"ACKNOWLEDGED","CORRECTED_AT_SOURCE","DUPLICATE_CONFIRMED","FALSE_POSITIVE","ESCALATED"}
ALLOWED_ROLES = {"reviewer","coordinator","admin"}

def _fp(v: Any) -> str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()

def _safe(v: str) -> str:
    v=str(v).strip()
    if not v or len(v)>128: raise ValueError("Identifier is required and must be <=128 characters.")
    return v

class GovernanceExceptionResolver:
    def __init__(self,database_path: str):
        self.ledger=AuditLedger(database_path)
        self.capture=AuditEventCapture(self.ledger)

    def resolve(self, *, exception_code: str, decision_kind: str, artifact_id: str,
                actor_id: str, role: str, outcome: str, reason_code: str,
                reconciliation_fingerprint: str) -> dict[str,Any]:
        if exception_code not in ALLOWED_CODES: raise ValueError("Unsupported exception code.")
        if role not in ALLOWED_ROLES: raise ValueError("Role is not authorized to resolve exceptions.")
        if outcome not in ALLOWED_OUTCOMES: raise ValueError("Unsupported resolution outcome.")
        artifact_id=_safe(artifact_id); actor_id=_safe(actor_id); decision_kind=_safe(decision_kind)
        reason_code=_safe(reason_code); reconciliation_fingerprint=_safe(reconciliation_fingerprint)
        event_id="RES-"+_fp({"code":exception_code,"kind":decision_kind,"artifact":artifact_id,"reconciliation":reconciliation_fingerprint})
        payload={"exception_code":exception_code,"decision_kind":decision_kind,"artifact_id":artifact_id,
                 "outcome":outcome,"reason_code":reason_code,"reconciliation_fingerprint":reconciliation_fingerprint,
                 "resolution_status":RESOLVED,"source_module":"governance_reconciliation","recorded_by_role":role,
                 "policy_version":POLICY_VERSION}
        return self.capture.record(event_id=event_id,event_type=RESOLUTION_EVENT,actor_id=actor_id,payload=payload)

    def list_resolutions(self, limit: int = 500) -> list[dict[str,Any]]:
        rows=[]
        for entry in self.ledger.list_entries(limit=min(max(int(limit),1),5000)):
            if entry.get("event_type")==RESOLUTION_EVENT:
                rows.append(entry)
        return rows
