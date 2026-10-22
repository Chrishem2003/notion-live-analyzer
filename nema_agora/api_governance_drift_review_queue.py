"""Phase 103 — governance drift review queue integration."""
from __future__ import annotations
import sqlite3
from typing import Any,Mapping
from .api_audit_binding import fingerprint
POLICY_VERSION="phase103-v1"
def build_drift_review_item(drift:Mapping[str,Any],priority:int|None=None)->dict[str,Any]:
 if not drift.get("drift_id") or not drift.get("drift_fingerprint"): raise ValueError("INVALID_DRIFT")
 if drift.get("state")!="REVIEW_TRIGGERED": raise ValueError("DRIFT_REVIEW_NOT_REQUIRED")
 p={"HIGH":90,"MEDIUM":60,"NONE":0}.get(drift.get("severity"),50) if priority is None else priority
 if not isinstance(p,int) or not 0<=p<=100: raise ValueError("INVALID_PRIORITY")
 payload={"drift_id":drift["drift_id"],"drift_fingerprint":drift["drift_fingerprint"],"baseline_snapshot_id":drift["baseline_snapshot_id"],"current_snapshot_id":drift["current_snapshot_id"],"severity":drift["severity"],"priority":p}
 return dict(payload,review_id="API-DRIFT-REVIEW-"+fingerprint(payload)[:24],state="QUEUED",policy_version=POLICY_VERSION,interpretation="API_GOVERNANCE_DRIFT_REVIEW_QUEUE",environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None)
class DriftReviewQueue:
 def __init__(self,database_path:str):
  if not database_path: raise ValueError("DATABASE_PATH_REQUIRED")
  self.db=sqlite3.connect(database_path)
  self.db.execute("CREATE TABLE IF NOT EXISTS governance_drift_review_queue(review_id TEXT PRIMARY KEY,drift_id TEXT NOT NULL,drift_fingerprint TEXT NOT NULL,baseline_snapshot_id TEXT NOT NULL,current_snapshot_id TEXT NOT NULL,severity TEXT NOT NULL,priority INTEGER NOT NULL,state TEXT NOT NULL,policy_version TEXT NOT NULL)")
  self.db.executescript("CREATE UNIQUE INDEX IF NOT EXISTS idx_drift_review_drift ON governance_drift_review_queue(drift_id); CREATE TRIGGER IF NOT EXISTS drift_review_no_update BEFORE UPDATE ON governance_drift_review_queue BEGIN SELECT RAISE(ABORT,'drift review queue is append-only'); END; CREATE TRIGGER IF NOT EXISTS drift_review_no_delete BEFORE DELETE ON governance_drift_review_queue BEGIN SELECT RAISE(ABORT,'drift review queue is append-only'); END;");self.db.commit()
 def enqueue(self,item:Mapping[str,Any])->dict[str,Any]:
  if item.get("state")!="QUEUED": raise ValueError("INVALID_QUEUE_ITEM")
  try:self.db.execute("INSERT INTO governance_drift_review_queue VALUES(?,?,?,?,?,?,?,?,?)",tuple(item[k] for k in ("review_id","drift_id","drift_fingerprint","baseline_snapshot_id","current_snapshot_id","severity","priority","state","policy_version")));self.db.commit()
  except sqlite3.IntegrityError as e: raise ValueError("DRIFT_REVIEW_ALREADY_QUEUED") from e
  return dict(item)
 def list(self,limit:int=500)->list[dict[str,Any]]:
  if not 1<=limit<=500: raise ValueError("INVALID_LIMIT")
  rows=self.db.execute("SELECT review_id,drift_id,drift_fingerprint,baseline_snapshot_id,current_snapshot_id,severity,priority,state,policy_version FROM governance_drift_review_queue ORDER BY priority DESC,review_id LIMIT ?",(limit,)).fetchall()
  return [dict(zip(("review_id","drift_id","drift_fingerprint","baseline_snapshot_id","current_snapshot_id","severity","priority","state","policy_version"),r)) for r in rows]
