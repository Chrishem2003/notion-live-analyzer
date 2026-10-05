"""Phase 113 — immutable human authorization ledger for recovery decisions."""
from __future__ import annotations
import re, sqlite3
from typing import Any, Mapping
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_review_lifecycle import validate_lifecycle
POLICY_VERSION="phase113-v1"
DECISIONS=("AUTHORIZE_NO_ACTION","AUTHORIZE_REVIEW_ONLY","AUTHORIZE_ESCALATION")
ROLES=("coordinator","admin")
_ID=re.compile(r"^[A-Za-z0-9._-]{1,128}$")
def authorize_recovery_decision(lifecycle: Mapping[str,Any], *, actor_id:str, role:str, decision:str, decided_at:str, rationale:str="")->dict[str,Any]:
    x=validate_lifecycle(lifecycle)
    if role not in ROLES: raise ValueError("UNAUTHORIZED_DECISION_ROLE")
    if not isinstance(actor_id,str) or not _ID.fullmatch(actor_id): raise ValueError("INVALID_ACTOR_ID")
    if decision not in DECISIONS: raise ValueError("INVALID_DECISION")
    if not isinstance(decided_at,str) or not decided_at.strip(): raise ValueError("DECISION_TIME_REQUIRED")
    if not isinstance(rationale,str) or len(rationale)>2000: raise ValueError("INVALID_RATIONALE")
    if decision=="AUTHORIZE_NO_ACTION" and x["lifecycle_state"]!="APPROVED_NO_ACTION": raise ValueError("NO_ACTION_REQUIRES_APPROVED_LIFECYCLE")
    if decision=="AUTHORIZE_ESCALATION" and x["lifecycle_state"]!="ESCALATED": raise ValueError("ESCALATION_REQUIRES_ESCALATED_LIFECYCLE")
    payload={"policy_version":POLICY_VERSION,"lifecycle_fingerprint":x["lifecycle_fingerprint"],"review_audit_id":x["review_audit_id"],"monitor_fingerprint":x["monitor_fingerprint"],"actor_id":actor_id,"role":role,"decision":decision,"decided_at":decided_at,"rationale":rationale,"human_authorized":True,"execution_permitted":False,"execution_performed":False,"environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None}
    return dict(payload,decision_fingerprint=fingerprint(payload),decision_id="NEMA-AGORA-DECISION-"+fingerprint(payload)[:24])
def validate_decision(decision:Mapping[str,Any])->dict[str,Any]:
    required=("policy_version","lifecycle_fingerprint","review_audit_id","monitor_fingerprint","actor_id","role","decision","decided_at","rationale","human_authorized","execution_permitted","execution_performed","decision_fingerprint","decision_id", "environmental_conclusion", "regulatory_conclusion", "enforcement_action")
    if not isinstance(decision,Mapping) or any(k not in decision for k in required): raise ValueError("DECISION_FIELDS_REQUIRED")
    if decision["policy_version"]!=POLICY_VERSION or decision["role"] not in ROLES or decision["decision"] not in DECISIONS: raise ValueError("INVALID_DECISION")
    if decision["human_authorized"] is not True or decision["execution_permitted"] is not False or decision["execution_performed"] is not False: raise ValueError("DECISION_CONTROL_VIOLATION")
    payload={k:decision[k] for k in required if k not in ("decision_fingerprint","decision_id")}
    fp=fingerprint(payload)
    if decision["decision_fingerprint"]!=fp or decision["decision_id"]!="NEMA-AGORA-DECISION-"+fp[:24]: raise ValueError("DECISION_FINGERPRINT_MISMATCH")
    return dict(decision)
class RecoveryDecisionLedger:
    def __init__(self,database_path:str):
        self.database_path=database_path
        with sqlite3.connect(database_path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS recovery_decision_ledger (decision_id TEXT PRIMARY KEY, decision_fingerprint TEXT UNIQUE NOT NULL, lifecycle_fingerprint TEXT UNIQUE NOT NULL, decision_json TEXT NOT NULL)")
            db.execute("CREATE TRIGGER IF NOT EXISTS recovery_decision_no_update BEFORE UPDATE ON recovery_decision_ledger BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END")
            db.execute("CREATE TRIGGER IF NOT EXISTS recovery_decision_no_delete BEFORE DELETE ON recovery_decision_ledger BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END")
    def append(self,decision:Mapping[str,Any])->dict[str,Any]:
        import json
        x=validate_decision(decision)
        with sqlite3.connect(self.database_path) as db:
            db.execute("INSERT INTO recovery_decision_ledger VALUES (?,?,?,?)",(x["decision_id"],x["decision_fingerprint"],x["lifecycle_fingerprint"],json.dumps(x,sort_keys=True)))
        return dict(x)
    def list(self,limit:int=100)->list[dict[str,Any]]:
        import json
        if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=500: raise ValueError("INVALID_LIMIT")
        with sqlite3.connect(self.database_path) as db: rows=db.execute("SELECT decision_json FROM recovery_decision_ledger ORDER BY rowid DESC LIMIT ?",(limit,)).fetchall()
        return [json.loads(r[0]) for r in rows]
    def count(self)->int:
        with sqlite3.connect(self.database_path) as db: return int(db.execute("SELECT COUNT(*) FROM recovery_decision_ledger").fetchone()[0])
