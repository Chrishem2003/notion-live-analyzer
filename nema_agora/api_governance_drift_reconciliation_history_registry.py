"""Phase 108 — append-only persistent reconciliation snapshot history registry."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from .api_governance_drift_reconciliation_history import (
    build_snapshot_history,
    validate_reconciliation_snapshot,
)

POLICY_VERSION = "phase108-v1"


class GovernanceDriftReconciliationHistoryRegistry:
    """Append-only SQLite store for validated Phase 107 snapshots.

    The database is a history store, not an authority source. Appends preserve
    the supplied snapshot and reject conflicting IDs, sequence numbers or hashes.
    """

    def __init__(self, database_path: str | Path):
        if not isinstance(database_path, (str, Path)) or not str(database_path).strip():
            raise ValueError("DATABASE_PATH_REQUIRED")
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS governance_drift_reconciliation_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    sequence INTEGER NOT NULL UNIQUE,
                    snapshot_fingerprint TEXT NOT NULL UNIQUE,
                    reconciliation_fingerprint TEXT NOT NULL,
                    state TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    registry_policy_version TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS governance_drift_reconciliation_snapshots_no_update
                BEFORE UPDATE ON governance_drift_reconciliation_snapshots
                BEGIN
                    SELECT RAISE(ABORT, 'reconciliation snapshot history is append-only');
                END
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS governance_drift_reconciliation_snapshots_no_delete
                BEFORE DELETE ON governance_drift_reconciliation_snapshots
                BEGIN
                    SELECT RAISE(ABORT, 'reconciliation snapshot history is append-only');
                END
                """
            )

    def append(self, snapshot: Mapping[str, Any]) -> dict[str, Any]:
        record = validate_reconciliation_snapshot(snapshot)
        encoded = json.dumps(dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        try:
            with self._connect() as conn:
                existing = conn.execute(
                    "SELECT 1 FROM governance_drift_reconciliation_snapshots WHERE snapshot_id=? OR snapshot_fingerprint=? LIMIT 1",
                    (record["snapshot_id"], record["snapshot_fingerprint"]),
                ).fetchone()
                if existing is not None:
                    raise ValueError("SNAPSHOT_HISTORY_CONFLICT")
                prior = conn.execute(
                    "SELECT sequence, snapshot_fingerprint FROM governance_drift_reconciliation_snapshots ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                if prior is None:
                    if record["sequence"] != 1 or record["previous_snapshot_fingerprint"] is not None:
                        raise ValueError("FIRST_SNAPSHOT_SEQUENCE_REQUIRED")
                else:
                    if record["sequence"] != prior["sequence"] + 1:
                        raise ValueError("SNAPSHOT_SEQUENCE_NOT_NEXT")
                    if record["previous_snapshot_fingerprint"] != prior["snapshot_fingerprint"]:
                        raise ValueError("SNAPSHOT_PREDECESSOR_MISMATCH")
                conn.execute(
                    """
                    INSERT INTO governance_drift_reconciliation_snapshots (
                        snapshot_id, sequence, snapshot_fingerprint,
                        reconciliation_fingerprint, state, captured_at,
                        snapshot_json, registry_policy_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["snapshot_id"], record["sequence"],
                        record["snapshot_fingerprint"], record["reconciliation_fingerprint"],
                        record["state"], record["captured_at"], encoded, POLICY_VERSION,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("SNAPSHOT_HISTORY_CONFLICT") from exc
        return dict(record, registry_policy_version=POLICY_VERSION)

    def list(self, limit: int = 500) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
            raise ValueError("INVALID_LIMIT")
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT snapshot_json, registry_policy_version
                FROM governance_drift_reconciliation_snapshots
                ORDER BY sequence ASC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            record = json.loads(row["snapshot_json"])
            record["registry_policy_version"] = row["registry_policy_version"]
            result.append(record)
        return result

    def reconcile_history(self) -> dict[str, Any]:
        """Return a read-only integrity summary for the currently persisted history."""
        records = self.list()
        snapshots = [{key: value for key, value in item.items() if key != "registry_policy_version"} for item in records]
        return build_snapshot_history(snapshots)

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM governance_drift_reconciliation_snapshots"
            ).fetchone()
        return int(row["total"])
