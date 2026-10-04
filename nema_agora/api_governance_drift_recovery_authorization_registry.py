"""Phase 116 — append-only persistent registry for governed authorization history."""
from __future__ import annotations
import json, sqlite3
from pathlib import Path
from typing import Any, Mapping
from .api_governance_drift_recovery_authorization_history import validate_authorization_snapshot, reconcile_authorization_history
POLICY_VERSION="phase116-v1"
class RecoveryAuthorizationHistoryRegistry:
    def __init__(self,database_path:str|Path):
        if not isinstance(database_path,(str,Path)) or not str(database_path).strip(): raise ValueError("DATABASE_PATH_REQUIRED")
        self.database_path=str(database_path); Path(self.database_path).parent.mkdir(parents=True,exist_ok=True); self._initialize()
    def _connect(self):
        c=sqlite3.connect(self.database_path); c.row_factory=sqlite3.Row; return c
    def _initialize(self):
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS recovery_authorization_history (snapshot_fingerprint TEXT PRIMARY KEY, sequence INTEGER NOT NULL UNIQUE, captured_at TEXT NOT NULL, snapshot_json TEXT NOT NULL, registry_policy_version TEXT NOT NULL)")
            db.execute("CREATE TRIGGER IF NOT EXISTS recovery_authorization_history_no_update BEFORE UPDATE ON recovery_authorization_history BEGIN SELECT RAISE(ABORT,'authorization history is append-only'); END")
            db.execute("CREATE TRIGGER IF NOT EXISTS recovery_authorization_history_no_delete BEFORE DELETE ON recovery_authorization_history BEGIN SELECT RAISE(ABORT,'authorization history is append-only'); END")
    def append(self,snapshot:Mapping[str,Any])->dict[str,Any]:
        x=validate_authorization_snapshot(snapshot)
        encoded=json.dumps(dict(x),sort_keys=True,separators=(",",":"),ensure_ascii=False)
        with self._connect() as db:
            prior=db.execute("SELECT sequence,snapshot_fingerprint FROM recovery_authorization_history ORDER BY sequence DESC LIMIT 1").fetchone()
            if prior is None:
                if x["sequence"]!=1 or x["previous_snapshot_fingerprint"] is not None: raise ValueError("FIRST_SNAPSHOT_SEQUENCE_REQUIRED")
            else:
                if x["sequence"]!=prior["sequence"]+1: raise ValueError("SNAPSHOT_SEQUENCE_NOT_NEXT")
                if x["previous_snapshot_fingerprint"]!=prior["snapshot_fingerprint"]: raise ValueError("SNAPSHOT_PREDECESSOR_MISMATCH")
            try: db.execute("INSERT INTO recovery_authorization_history VALUES (?,?,?,?,?)",(x["snapshot_fingerprint"],x["sequence"],x["captured_at"],encoded,POLICY_VERSION))
            except sqlite3.IntegrityError as exc: raise ValueError("SNAPSHOT_HISTORY_CONFLICT") from exc
        return dict(x,registry_policy_version=POLICY_VERSION)
    def list(self,limit:int=500)->list[dict[str,Any]]:
        if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=500: raise ValueError("INVALID_LIMIT")
        with self._connect() as db: rows=db.execute("SELECT snapshot_json,registry_policy_version FROM recovery_authorization_history ORDER BY sequence ASC LIMIT ?",(limit,)).fetchall()
        out=[]
        for row in rows:
            x=json.loads(row["snapshot_json"]); x["registry_policy_version"]=row["registry_policy_version"]; out.append(x)
        return out
    def reconcile_history(self)->dict[str,Any]:
        records=self.list(); snapshots=[{k:v for k,v in x.items() if k!="registry_policy_version"} for x in records]
        return reconcile_authorization_history(snapshots)
    def count(self)->int:
        with self._connect() as db: return int(db.execute("SELECT COUNT(*) FROM recovery_authorization_history").fetchone()[0])
