"""Phase 156 — persistent append-only registry for Phase 155 continuity snapshots."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_continuity_phase155 import validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity_snapshot

POLICY_VERSION = "phase156-v1"
TABLE = "lifecycle_decision_continuity_review_lifecycle_decision_continuity"

class LifecycleDecisionContinuityRegistry:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.database_path)

    def _initialize(self):
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence INTEGER NOT NULL UNIQUE,
                snapshot_fingerprint TEXT NOT NULL UNIQUE,
                captured_at TEXT NOT NULL,
                previous_snapshot_fingerprint TEXT,
                decision_count INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            conn.execute(f"""CREATE TRIGGER IF NOT EXISTS {TABLE}_no_update
                BEFORE UPDATE ON {TABLE} BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END""")
            conn.execute(f"""CREATE TRIGGER IF NOT EXISTS {TABLE}_no_delete
                BEFORE DELETE ON {TABLE} BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END""")

    def append(self, snapshot: Mapping[str, Any]) -> dict[str, Any]:
        snapshot = validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity_snapshot(snapshot)
        with self._connect() as conn:
            conn.execute(f"INSERT INTO {TABLE}(sequence,snapshot_fingerprint,captured_at,previous_snapshot_fingerprint,decision_count,snapshot_json) VALUES (?,?,?,?,?,?)",
                         (snapshot["sequence"], snapshot["snapshot_fingerprint"], snapshot["captured_at"], snapshot["previous_snapshot_fingerprint"], snapshot["decision_count"], json.dumps(snapshot, sort_keys=True, separators=(",", ":"))))
        return dict(snapshot)

    def list(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(f"SELECT snapshot_json FROM {TABLE} ORDER BY sequence").fetchall()
        return [json.loads(row[0]) for row in rows]

    def count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0])

    def validate(self) -> list[dict[str, Any]]:
        return [validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity_snapshot(s) for s in self.list()]
