"""Phase 64 — append-only audit registry for spatial human-review events."""
from __future__ import annotations
import sqlite3
from typing import Any
from nema_agora.spatial_change_human_review import create_review_event
class SpatialReviewAuditRegistry:
 def __init__(self,database_path:str):
  self.database_path=str(database_path).strip()
  if not self.database_path:raise ValueError("Explicit database path required.")
  with sqlite3.connect(self.database_path) as db:
   db.execute("CREATE TABLE IF NOT EXISTS spatial_review_audit (review_event_id TEXT PRIMARY KEY,review_item_id TEXT NOT NULL UNIQUE,candidate_id TEXT NOT NULL,source_queue_fingerprint TEXT NOT NULL,reviewer_id TEXT NOT NULL,reviewer_role TEXT NOT NULL,outcome TEXT NOT NULL,notes TEXT NOT NULL,reviewed_at TEXT NOT NULL,audit_event_type TEXT NOT NULL,human_decision INTEGER NOT NULL,event_fingerprint TEXT NOT NULL,policy_version TEXT NOT NULL)")
   db.execute("CREATE TRIGGER IF NOT EXISTS spatial_review_audit_immutable_update BEFORE UPDATE ON spatial_review_audit BEGIN SELECT RAISE(ABORT,'spatial review audit is append-only'); END")
   db.execute("CREATE TRIGGER IF NOT EXISTS spatial_review_audit_immutable_delete BEFORE DELETE ON spatial_review_audit BEGIN SELECT RAISE(ABORT,'spatial review audit is append-only'); END")
 def record(self,**kwargs)->dict[str,Any]:
  event=create_review_event(**kwargs)
  if event["state"]!="VALID":return event
  keys=("review_event_id","review_item_id","candidate_id","source_queue_fingerprint","reviewer_id","reviewer_role","outcome","notes","reviewed_at","audit_event_type")
  values=tuple(event[k] for k in keys)+(1,event["event_fingerprint"],event["policy_version"])
  with sqlite3.connect(self.database_path) as db:
   try:db.execute("INSERT INTO spatial_review_audit VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",values)
   except sqlite3.IntegrityError as exc:raise ValueError("REVIEW_ALREADY_RECORDED") from exc
  return event
 def list(self,limit:int=500)->list[dict[str,Any]]:
  with sqlite3.connect(self.database_path) as db:
   db.row_factory=sqlite3.Row
   return [dict(x) for x in db.execute("SELECT * FROM spatial_review_audit ORDER BY reviewed_at DESC,review_event_id DESC LIMIT ?",(max(1,min(int(limit),5000)),)).fetchall()]
