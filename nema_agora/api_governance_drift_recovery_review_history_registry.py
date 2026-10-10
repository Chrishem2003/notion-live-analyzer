"""Phase 112 — append-only SQLite registry for Phase 112 snapshots."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from .api_governance_drift_recovery_review_history import (
    POLICY_VERSION, reconcile_recovery_review_snapshot_history,
    validate_recovery_review_snapshot,
)


class RecoveryReviewSnapshotHistoryRegistry:
    """Persist validated snapshots with strict sequence and predecessor binding."""

    def __init__(self, database_path: str | Path):
        if not isinstance(database_path, (str, Path)) or not str(database_path).strip():
            raise ValueError("DATABASE_PATH_REQUIRED")
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS recovery_review_snapshot_history (
                snapshot_id TEXT PRIMARY KEY,
                sequence INTEGER NOT NULL UNIQUE,
                snapshot_fingerprint TEXT NOT NULL UNIQUE,
                predecessor_fingerprint TEXT,
                snapshot_json TEXT NOT NULL,
                policy_version TEXT NOT NULL
            )""")
            conn.execute("""CREATE TRIGGER IF NOT EXISTS recovery_review_snapshot_no_update
                BEFORE UPDATE ON recovery_review_snapshot_history BEGIN
                SELECT RAISE(ABORT, 'recovery review snapshot history is append-only'); END""")
            conn.execute("""CREATE TRIGGER IF NOT EXISTS recovery_review_snapshot_no_delete
                BEFORE DELETE ON recovery_review_snapshot_history BEGIN
                SELECT RAISE(ABORT, 'recovery review snapshot history is append-only'); END""")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def append(self, snapshot: Mapping[str, Any]) -> dict[str, Any]:
        item = validate_recovery_review_snapshot(snapshot)
        with self._connect() as conn:
            row = conn.execute("SELECT sequence, snapshot_fingerprint FROM recovery_review_snapshot_history ORDER BY sequence DESC LIMIT 1").fetchone()
            expected_sequence = 1 if row is None else int(row["sequence"]) + 1
            expected_predecessor = None if row is None else row["snapshot_fingerprint"]
            if item["sequence"] != expected_sequence:
                raise ValueError("INVALID_NEXT_SEQUENCE")
            if item.get("predecessor_fingerprint") != expected_predecessor:
                raise ValueError("PREDECESSOR_FINGERPRINT_MISMATCH")
            encoded = json.dumps(dict(item), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            try:
                conn.execute("""INSERT INTO recovery_review_snapshot_history
                    (snapshot_id, sequence, snapshot_fingerprint, predecessor_fingerprint, snapshot_json, policy_version)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (item["snapshot_id"], item["sequence"], item["snapshot_fingerprint"],
                     item.get("predecessor_fingerprint"), encoded, POLICY_VERSION))
            except sqlite3.IntegrityError as exc:
                raise ValueError("SNAPSHOT_HISTORY_CONFLICT") from exc
        return dict(item)

    def list(self, limit: int = 500) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
            raise ValueError("INVALID_LIMIT")
        with self._connect() as conn:
            rows = conn.execute("SELECT snapshot_json FROM recovery_review_snapshot_history ORDER BY sequence ASC LIMIT ?", (limit,)).fetchall()
        return [json.loads(row["snapshot_json"]) for row in rows]

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM recovery_review_snapshot_history").fetchone()
        return int(row["total"])

    def integrity_report(self) -> dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute("SELECT snapshot_json, policy_version FROM recovery_review_snapshot_history ORDER BY sequence ASC").fetchall()
        snapshots = []
        for row in rows:
            item = json.loads(row["snapshot_json"])
            if row["policy_version"] != POLICY_VERSION:
                item["policy_version"] = "invalid-persisted-policy"
            snapshots.append(item)
        return reconcile_recovery_review_snapshot_history(snapshots)
