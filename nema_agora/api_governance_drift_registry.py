"""Phase 102 — persistent append-only API governance drift registry."""
from __future__ import annotations
import sqlite3
from typing import Any,Mapping
from .api_audit_binding import fingerprint
POLICY_VERSION="phase102-v1"
def validate_drift(d:Mapping[str,Any])->None:
 if not isinstance(d,Mapping) or not d.get("drift_id") or not d.get("drift_fingerprint"): raise ValueError("INVALID_DRIFT")
 if d.get("policy_version") != "phase101-v1": raise ValueError("DRIFT_POLICY_MISMATCH")
 if d.get("state") not in {"NO_DRIFT","REVIEW_TRIGGERED"}: raise ValueError("INVALID_DRIFT_STATE")
 if not d.get("baseline_snapshot_id") or not d.get("current_snapshot_id"): raise ValueError("INVALID_SNAPSHOT_BINDING")
 if not isinstance(d.get("drift_detected"), bool): raise ValueError("INVALID_DRIFT_FLAG")
 if not isinstance(d.get("review_required"), bool) or d["review_required"] != d["drift_detected"]: raise ValueError("INVALID_REVIEW_REQUIREMENT")
 expected_state = "REVIEW_TRIGGERED" if d["drift_detected"] else "NO_DRIFT"
 if d["state"] != expected_state: raise ValueError("DRIFT_STATE_MISMATCH")
 if d.get("severity") not in {"HIGH", "MEDIUM", "NONE"}: raise ValueError("INVALID_DRIFT_SEVERITY")
 if (not isinstance(d.get("changes"), list)
     or (d["drift_detected"] != bool(d["changes"]))
     or (not d["drift_detected"] and d["severity"] != "NONE")
     or (d["drift_detected"] and d["severity"] == "NONE")):
  raise ValueError("INVALID_DRIFT_CHANGES")
 payload = {
  "policy_version": d["policy_version"],
  "baseline_snapshot_id": d["baseline_snapshot_id"],
  "current_snapshot_id": d["current_snapshot_id"],
  "drift_detected": d["drift_detected"],
  "severity": d["severity"],
  "changes": d["changes"],
  "review_required": d["review_required"],
 }
 expected_fingerprint = fingerprint(payload)
 if d["drift_fingerprint"] != expected_fingerprint: raise ValueError("DRIFT_FINGERPRINT_MISMATCH")
 if d["drift_id"] != "API-DRIFT-" + expected_fingerprint[:24]: raise ValueError("DRIFT_ID_MISMATCH")
class GovernanceDriftRegistry:
 def __init__(self,database_path:str):
  if not database_path: raise ValueError("DATABASE_PATH_REQUIRED")
  self.db=sqlite3.connect(database_path);self.db.execute("""CREATE TABLE IF NOT EXISTS governance_drift_events(drift_id TEXT PRIMARY KEY,baseline_snapshot_id TEXT NOT NULL,current_snapshot_id TEXT NOT NULL,state TEXT NOT NULL,severity TEXT NOT NULL,review_required INTEGER NOT NULL,changes_json TEXT NOT NULL,drift_fingerprint TEXT UNIQUE NOT NULL,policy_version TEXT NOT NULL)""")
  self.db.executescript("""CREATE TRIGGER IF NOT EXISTS governance_drift_no_update BEFORE UPDATE ON governance_drift_events BEGIN SELECT RAISE(ABORT,'governance drift registry is append-only'); END; CREATE TRIGGER IF NOT EXISTS governance_drift_no_delete BEFORE DELETE ON governance_drift_events BEGIN SELECT RAISE(ABORT,'governance drift registry is append-only'); END;""");self.db.commit()
 def append(self,d:Mapping[str,Any])->dict[str,Any]:
  validate_drift(d)
  try:self.db.execute("INSERT INTO governance_drift_events VALUES(?,?,?,?,?,?,?,?,?)",(d["drift_id"],d["baseline_snapshot_id"],d["current_snapshot_id"],d["state"],d["severity"],int(bool(d["review_required"])),__import__("json").dumps(d.get("changes",[]),sort_keys=True,separators=(",",":")),d["drift_fingerprint"],POLICY_VERSION));self.db.commit()
  except sqlite3.IntegrityError as e: raise ValueError("DRIFT_EVENT_CONFLICT") from e
  return dict(d,policy_version=POLICY_VERSION)
 def list(self,limit:int=500)->list[dict[str,Any]]:
  if not 1<=limit<=500: raise ValueError("INVALID_LIMIT")
  rows=self.db.execute("SELECT drift_id,baseline_snapshot_id,current_snapshot_id,state,severity,review_required,changes_json,drift_fingerprint,policy_version FROM governance_drift_events ORDER BY rowid LIMIT ?",(limit,)).fetchall()
  return [{"drift_id":r[0],"baseline_snapshot_id":r[1],"current_snapshot_id":r[2],"state":r[3],"severity":r[4],"review_required":bool(r[5]),"changes":__import__("json").loads(r[6]),"drift_fingerprint":r[7],"policy_version":r[8]} for r in rows]
