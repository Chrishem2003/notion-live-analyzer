"""Phase 96 — authorized human review and audit binding."""
from __future__ import annotations
import sqlite3
from typing import Any,Mapping
from .api_audit_binding import fingerprint
POLICY_VERSION="phase96-v1"
OUTCOMES={"CONFIRMED_TRACE","NOT_CONFIRMED","INSUFFICIENT_EVIDENCE","ESCALATED"}
ROLES={"coordinator","admin"}
def review_queue_item(item:Mapping[str,Any],*,actor_id:str,role:str,outcome:str,reviewed_at:str)->dict[str,Any]:
 if item.get("state")!="QUEUED":return {"state":"CONTROL_REQUIRED","reason_code":"QUEUE_ITEM_NOT_READY"}
 if role not in ROLES or not isinstance(actor_id,str) or not actor_id.strip():return {"state":"CONTROL_REQUIRED","reason_code":"UNAUTHORIZED_REVIEWER"}
 if outcome not in OUTCOMES:return {"state":"CONTROL_REQUIRED","reason_code":"UNSUPPORTED_OUTCOME"}
 if not isinstance(reviewed_at,str) or not reviewed_at.strip():return {"state":"CONTROL_REQUIRED","reason_code":"INVALID_REVIEW_TIME"}
 payload={"review_id":item.get("review_id"),"case_id":item.get("case_id"),"case_fingerprint":item.get("case_fingerprint"),"request_id":item.get("request_id"),"reviewer_actor_id":actor_id,"reviewer_role":role,"outcome":outcome,"reviewed_at":reviewed_at}
 return dict(payload,audit_id="API-REVIEW-AUDIT-"+fingerprint(payload)[:24],audit_fingerprint=fingerprint(payload),state="REVIEW_RECORDED",policy_version=POLICY_VERSION,interpretation="API_GOVERNANCE_HUMAN_REVIEW",environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None)
class ApiHumanReviewAuditRegistry:
 def __init__(self,database_path:str):
  self.database_path=database_path
  if not database_path:raise ValueError("DATABASE_PATH_REQUIRED")
  with sqlite3.connect(database_path) as c:
   c.execute("""CREATE TABLE IF NOT EXISTS api_governance_review_audits(
    audit_id TEXT PRIMARY KEY,review_id TEXT NOT NULL UNIQUE,case_id TEXT NOT NULL,case_fingerprint TEXT NOT NULL,
    request_id TEXT NOT NULL,reviewer_actor_id TEXT NOT NULL,reviewer_role TEXT NOT NULL,outcome TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,audit_fingerprint TEXT NOT NULL UNIQUE,policy_version TEXT NOT NULL)""")
   c.execute("""CREATE TRIGGER IF NOT EXISTS api_review_audit_no_update BEFORE UPDATE ON api_governance_review_audits BEGIN SELECT RAISE(ABORT,'api human review audit is append-only'); END""")
   c.execute("""CREATE TRIGGER IF NOT EXISTS api_review_audit_no_delete BEFORE DELETE ON api_governance_review_audits BEGIN SELECT RAISE(ABORT,'api human review audit is append-only'); END""")
 def append(self,audit:Mapping[str,Any])->dict[str,Any]:
  if audit.get("state")!="REVIEW_RECORDED":raise ValueError("INVALID_REVIEW_AUDIT")
  try:
   with sqlite3.connect(self.database_path) as c:c.execute("INSERT INTO api_governance_review_audits VALUES (?,?,?,?,?,?,?,?,?,?,?)",tuple(audit[k] for k in ("audit_id","review_id","case_id","case_fingerprint","request_id","reviewer_actor_id","reviewer_role","outcome","reviewed_at","audit_fingerprint","policy_version")))
  except sqlite3.IntegrityError as exc:raise ValueError("REVIEW_ALREADY_RECORDED") from exc
  return dict(audit)
 def list(self)->list[dict[str,Any]]:
  with sqlite3.connect(self.database_path) as c:
   c.row_factory=sqlite3.Row
   return [dict(r) for r in c.execute("SELECT * FROM api_governance_review_audits ORDER BY reviewed_at,audit_id").fetchall()]
