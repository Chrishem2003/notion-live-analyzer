"""Phase 95 — API governance review queue."""
from __future__ import annotations
import sqlite3
from typing import Any,Mapping
from .api_audit_binding import fingerprint
POLICY_VERSION="phase95-v1"
def build_review_item(case:Mapping[str,Any],priority:int=50)->dict[str,Any]:
 if case.get("state")!="CASEBOOK_READY": return {"state":"CONTROL_REQUIRED","reason_code":"CASEBOOK_REQUIRED"}
 if not isinstance(priority,int) or not 0<=priority<=100:return {"state":"CONTROL_REQUIRED","reason_code":"INVALID_PRIORITY"}
 payload={"case_id":case.get("case_id"),"case_fingerprint":case.get("case_fingerprint"),"request_id":case.get("request_id"),"priority":priority}
 return dict(payload,review_id="API-REVIEW-"+fingerprint(payload)[:24],state="QUEUED",policy_version=POLICY_VERSION,interpretation="API_GOVERNANCE_REVIEW_QUEUE",environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None)
class ApiGovernanceReviewQueue:
 def __init__(self,database_path:str):
  if not database_path:raise ValueError("DATABASE_PATH_REQUIRED")
  self.database_path=database_path
  with sqlite3.connect(database_path) as c:
   c.execute("""CREATE TABLE IF NOT EXISTS api_governance_review_queue(
    review_id TEXT PRIMARY KEY,case_id TEXT NOT NULL,case_fingerprint TEXT NOT NULL,request_id TEXT NOT NULL,
    priority INTEGER NOT NULL,state TEXT NOT NULL,policy_version TEXT NOT NULL)""")
   c.execute("""CREATE TRIGGER IF NOT EXISTS api_review_no_update BEFORE UPDATE ON api_governance_review_queue BEGIN SELECT RAISE(ABORT,'api governance review queue is append-only'); END""")
   c.execute("""CREATE TRIGGER IF NOT EXISTS api_review_no_delete BEFORE DELETE ON api_governance_review_queue BEGIN SELECT RAISE(ABORT,'api governance review queue is append-only'); END""")
 def enqueue(self,item:Mapping[str,Any])->dict[str,Any]:
  if item.get("state")!="QUEUED":raise ValueError("INVALID_REVIEW_ITEM")
  try:
   with sqlite3.connect(self.database_path) as c:c.execute("INSERT INTO api_governance_review_queue VALUES (?,?,?,?,?,?,?)",tuple(item[k] for k in ("review_id","case_id","case_fingerprint","request_id","priority","state","policy_version")))
  except sqlite3.IntegrityError as exc:raise ValueError("API_REVIEW_ALREADY_QUEUED") from exc
  return dict(item)
 def list(self)->list[dict[str,Any]]:
  with sqlite3.connect(self.database_path) as c:
   c.row_factory=sqlite3.Row
   return [dict(r) for r in c.execute("SELECT * FROM api_governance_review_queue ORDER BY priority DESC,review_id").fetchall()]
