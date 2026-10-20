"""Phase 148 — persistent append-only registry for Phase 147 continuity snapshots."""
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any, Mapping
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_phase147 import validate_authorization_history_registry_decision_history_lifecycle_decision_snapshot

POLICY_VERSION="phase148-v1"
TABLE="authorization_history_registry_decision_history_lifecycle_decision_continuity"

class AuthorizationHistoryRegistryDecisionHistoryLifecycleDecisionContinuityRegistry:
    def __init__(self,database_path:str|Path):
        self.database_path=str(database_path)
        Path(self.database_path).parent.mkdir(parents=True,exist_ok=True)
        with self._connect() as db:
            db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE}(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence INTEGER NOT NULL UNIQUE,
                snapshot_fingerprint TEXT NOT NULL UNIQUE,
                captured_at TEXT NOT NULL,
                previous_snapshot_fingerprint TEXT,
                decision_count INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            db.execute(f"""CREATE TRIGGER IF NOT EXISTS {TABLE}_no_update
                BEFORE UPDATE ON {TABLE} BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END""")
            db.execute(f"""CREATE TRIGGER IF NOT EXISTS {TABLE}_no_delete
                BEFORE DELETE ON {TABLE} BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END""")

    def _connect(self):
        return sqlite3.connect(self.database_path)

    def append(self,snapshot:Mapping[str,Any])->dict[str,Any]:
        import json
        item=validate_authorization_history_registry_decision_history_lifecycle_decision_snapshot(snapshot)
        with self._connect() as db:
            db.execute(f"INSERT INTO {TABLE}(sequence,snapshot_fingerprint,captured_at,previous_snapshot_fingerprint,decision_count,snapshot_json) VALUES(?,?,?,?,?,?)",
                (item["sequence"],item["snapshot_fingerprint"],item["captured_at"],item["previous_snapshot_fingerprint"],item["decision_count"],json.dumps(item,sort_keys=True,separators=(",",":"))))
        return dict(item)

    def list(self)->list[dict[str,Any]]:
        import json
        with self._connect() as db:
            rows=db.execute(f"SELECT snapshot_json FROM {TABLE} ORDER BY sequence").fetchall()
        return [json.loads(row[0]) for row in rows]

    def count(self)->int:
        with self._connect() as db:
            return int(db.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0])

    def validate(self)->list[dict[str,Any]]:
        return [validate_authorization_history_registry_decision_history_lifecycle_decision_snapshot(x) for x in self.list()]
