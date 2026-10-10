"""Phase 89 — persistent append-only API audit registry."""
from __future__ import annotations
import hashlib,json,sqlite3
from typing import Any,Mapping
from .api_audit_binding import POLICY_VERSION,fingerprint
def validate_event(event:Mapping[str,Any])->None:
 required=("event_id","request_id","actor_id","role","permission","authorization_fingerprint","query_fingerprint","result_fingerprint","occurred_at","policy_version")
 if any(not isinstance(event.get(k),str) or not event[k].strip() for k in required): raise ValueError("INVALID_AUDIT_EVENT")
 for k in ("authorization_fingerprint","query_fingerprint","result_fingerprint"):
  if len(event[k])!=64 or any(c not in "0123456789abcdef" for c in event[k]): raise ValueError("INVALID_FINGERPRINT")
def event_fingerprint(event:Mapping[str,Any])->str:
 return fingerprint({k:v for k,v in event.items() if k!="audit_fingerprint"})
class ApiAuditRegistry:
 def __init__(self,database_path:str):
  if not database_path: raise ValueError("DATABASE_PATH_REQUIRED")
  self.database_path=database_path
  with sqlite3.connect(database_path) as c:
   c.execute("""CREATE TABLE IF NOT EXISTS api_audit_events (
    event_id TEXT PRIMARY KEY, request_id TEXT NOT NULL, actor_id TEXT NOT NULL,
    role TEXT NOT NULL, permission TEXT NOT NULL, authorization_fingerprint TEXT NOT NULL,
    query_fingerprint TEXT NOT NULL, result_fingerprint TEXT NOT NULL, http_status INTEGER NOT NULL,
    outcome TEXT NOT NULL, occurred_at TEXT NOT NULL, policy_version TEXT NOT NULL,
    audit_fingerprint TEXT NOT NULL UNIQUE)""")
   c.execute("""CREATE TRIGGER IF NOT EXISTS api_audit_no_update
    BEFORE UPDATE ON api_audit_events BEGIN SELECT RAISE(ABORT,'api audit registry is append-only'); END""")
   c.execute("""CREATE TRIGGER IF NOT EXISTS api_audit_no_delete
    BEFORE DELETE ON api_audit_events BEGIN SELECT RAISE(ABORT,'api audit registry is append-only'); END""")
 def append(self,event:Mapping[str,Any])->dict[str,Any]:
  validate_event(event)
  row=dict(event); row.setdefault("http_status",0); row.setdefault("outcome","UNKNOWN")
  row["audit_fingerprint"]=event_fingerprint(row)
  try:
   with sqlite3.connect(self.database_path) as c:
    c.execute("""INSERT INTO api_audit_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
      tuple(row[k] for k in ("event_id","request_id","actor_id","role","permission","authorization_fingerprint","query_fingerprint","result_fingerprint","http_status","outcome","occurred_at","policy_version","audit_fingerprint")))
  except sqlite3.IntegrityError as exc: raise ValueError("API_AUDIT_EVENT_CONFLICT") from exc
  return row
 def list(self,request_id:str|None=None,limit:int=500)->list[dict[str,Any]]:
  if not 1<=limit<=500: raise ValueError("INVALID_LIMIT")
  with sqlite3.connect(self.database_path) as c:
   c.row_factory=sqlite3.Row
   if request_id:
    rows=c.execute("SELECT * FROM api_audit_events WHERE request_id=? ORDER BY occurred_at,event_id LIMIT ?",(request_id,limit)).fetchall()
   else: rows=c.execute("SELECT * FROM api_audit_events ORDER BY occurred_at,event_id LIMIT ?",(limit,)).fetchall()
  return [dict(r) for r in rows]
