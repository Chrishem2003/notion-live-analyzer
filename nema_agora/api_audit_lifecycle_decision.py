"""Phase 92 — human-governed API audit lifecycle decision ledger."""
from __future__ import annotations
import sqlite3
from typing import Any,Mapping
from .api_audit_binding import fingerprint
POLICY_VERSION="phase92-v1"
DECISIONS={"RECONCILE","REQUEST_REVIEW","RETAIN","EXPIRE"}
ROLES={"coordinator","admin"}
def validate_decision(*,event:Mapping[str,Any],reconciliation:Mapping[str,Any],lifecycle:Mapping[str,Any],decision:str,actor_id:str,role:str)->dict[str,Any]:
 if decision not in DECISIONS:return {"state":"CONTROL_REQUIRED","reason_code":"UNSUPPORTED_DECISION"}
 if role not in ROLES or not isinstance(actor_id,str) or not actor_id.strip():return {"state":"CONTROL_REQUIRED","reason_code":"UNAUTHORIZED_ACTOR"}
 if lifecycle.get("event_id")!=event.get("event_id") or lifecycle.get("reconciliation_fingerprint")!=reconciliation.get("reconciliation_fingerprint"):return {"state":"CONTROL_REQUIRED","reason_code":"SNAPSHOT_MISMATCH"}
 if reconciliation.get("state")!="RECONCILED":return {"state":"CONTROL_REQUIRED","reason_code":"RECONCILIATION_REQUIRED"}
 payload={"event_id":event.get("event_id"),"request_id":event.get("request_id"),"reconciliation_fingerprint":reconciliation.get("reconciliation_fingerprint"),"lifecycle_fingerprint":lifecycle.get("lifecycle_fingerprint"),"decision":decision,"actor_id":actor_id,"role":role}
 return dict(payload,decision_id="API-LIFE-DEC-"+fingerprint(payload)[:24],decision_fingerprint=fingerprint(payload),policy_version=POLICY_VERSION,state="DECISION_RECORDED",interpretation="API_AUDIT_LIFECYCLE_DECISION",environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None)
class LifecycleDecisionRegistry:
 def __init__(self,database_path:str):
  if not database_path:raise ValueError("DATABASE_PATH_REQUIRED")
  self.database_path=database_path
  with sqlite3.connect(database_path) as c:
   c.execute("""CREATE TABLE IF NOT EXISTS api_audit_lifecycle_decisions(
    decision_id TEXT PRIMARY KEY,event_id TEXT NOT NULL,request_id TEXT NOT NULL,
    reconciliation_fingerprint TEXT NOT NULL,lifecycle_fingerprint TEXT NOT NULL,
    decision TEXT NOT NULL,actor_id TEXT NOT NULL,role TEXT NOT NULL,
    decision_fingerprint TEXT NOT NULL UNIQUE,policy_version TEXT NOT NULL)""")
   c.execute("""CREATE TRIGGER IF NOT EXISTS api_lifecycle_decision_no_update BEFORE UPDATE ON api_audit_lifecycle_decisions BEGIN SELECT RAISE(ABORT,'lifecycle decision ledger is append-only'); END""")
   c.execute("""CREATE TRIGGER IF NOT EXISTS api_lifecycle_decision_no_delete BEFORE DELETE ON api_audit_lifecycle_decisions BEGIN SELECT RAISE(ABORT,'lifecycle decision ledger is append-only'); END""")
 def append(self,decision:Mapping[str,Any])->dict[str,Any]:
  if decision.get("state")!="DECISION_RECORDED":raise ValueError("INVALID_DECISION")
  try:
   with sqlite3.connect(self.database_path) as c:c.execute("INSERT INTO api_audit_lifecycle_decisions VALUES (?,?,?,?,?,?,?,?,?,?)",tuple(decision[k] for k in ("decision_id","event_id","request_id","reconciliation_fingerprint","lifecycle_fingerprint","decision","actor_id","role","decision_fingerprint","policy_version")))
  except sqlite3.IntegrityError as exc:raise ValueError("LIFECYCLE_DECISION_CONFLICT") from exc
  return dict(decision)
 def list(self,event_id:str|None=None)->list[dict[str,Any]]:
  with sqlite3.connect(self.database_path) as c:
   c.row_factory=sqlite3.Row
   rows=c.execute("SELECT * FROM api_audit_lifecycle_decisions"+(" WHERE event_id=?","" )[0]+(" ORDER BY decision_id", (event_id,) if event_id else ()) if False else ("SELECT * FROM api_audit_lifecycle_decisions WHERE event_id=? ORDER BY decision_id", (event_id,)) if event_id else ("SELECT * FROM api_audit_lifecycle_decisions ORDER BY decision_id",())).fetchall()
  return [dict(r) for r in rows]
