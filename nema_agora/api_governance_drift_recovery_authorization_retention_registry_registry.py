"""Phase 132 — append-only persistent registry for Phase 131 authorization history."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from .api_governance_drift_recovery_authorization_retention_registry_history import (
    reconcile_retention_registry_authorization_history,
    validate_retention_registry_authorization_snapshot,
)

POLICY_VERSION = "phase132-v1"


class RetentionRegistryAuthorizationHistoryRegistry:
    """Persist Phase 131 snapshots as immutable evidence, never as execution authority."""

    def __init__(self, database_path: str | Path):
        if not isinstance(database_path, (str, Path)) or not str(database_path).strip():
            raise ValueError("DATABASE_PATH_REQUIRED")
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        db = sqlite3.connect(self.database_path)
        db.row_factory = sqlite3.Row
        return db

    def _initialize(self):
        with self._connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS retention_registry_authorization_history "
                "(snapshot_fingerprint TEXT PRIMARY KEY, sequence INTEGER NOT NULL UNIQUE, "
                "captured_at TEXT NOT NULL, snapshot_json TEXT NOT NULL, registry_policy_version TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TRIGGER IF NOT EXISTS retention_registry_authorization_history_no_update "
                "BEFORE UPDATE ON retention_registry_authorization_history BEGIN "
                "SELECT RAISE(ABORT,'retention registry authorization history is append-only'); END"
            )
            db.execute(
                "CREATE TRIGGER IF NOT EXISTS retention_registry_authorization_history_no_delete "
                "BEFORE DELETE ON retention_registry_authorization_history BEGIN "
                "SELECT RAISE(ABORT,'retention registry authorization history is append-only'); END"
            )

    def append(self, snapshot: Mapping[str, Any]) -> dict[str, Any]:
        item = validate_retention_registry_authorization_snapshot(snapshot)
        encoded = json.dumps(dict(item), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with self._connect() as db:
            previous = db.execute(
                "SELECT sequence,snapshot_fingerprint FROM retention_registry_authorization_history "
                "ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            if previous is None:
                if item["sequence"] != 1 or item["previous_snapshot_fingerprint"] is not None:
                    raise ValueError("FIRST_SNAPSHOT_SEQUENCE_REQUIRED")
            else:
                if item["sequence"] != previous["sequence"] + 1:
                    raise ValueError("SNAPSHOT_SEQUENCE_NOT_NEXT")
                if item["previous_snapshot_fingerprint"] != previous["snapshot_fingerprint"]:
                    raise ValueError("SNAPSHOT_PREDECESSOR_MISMATCH")
            try:
                db.execute(
                    "INSERT INTO retention_registry_authorization_history VALUES (?,?,?,?,?)",
                    (
                        item["snapshot_fingerprint"],
                        item["sequence"],
                        item["captured_at"],
                        encoded,
                        POLICY_VERSION,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("SNAPSHOT_HISTORY_CONFLICT") from exc
        return dict(item, registry_policy_version=POLICY_VERSION)

    def list(self, limit: int = 500) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
            raise ValueError("INVALID_LIMIT")
        with self._connect() as db:
            rows = db.execute(
                "SELECT snapshot_json,registry_policy_version "
                "FROM retention_registry_authorization_history ORDER BY sequence ASC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            item = json.loads(row["snapshot_json"])
            item["registry_policy_version"] = row["registry_policy_version"]
            result.append(item)
        return result

    def reconcile_history(self) -> dict[str, Any]:
        records = self.list()
        snapshots = [
            {k: v for k, v in item.items() if k != "registry_policy_version"}
            for item in records
        ]
        return reconcile_retention_registry_authorization_history(snapshots)

    def count(self) -> int:
        with self._connect() as db:
            return int(
                db.execute(
                    "SELECT COUNT(*) FROM retention_registry_authorization_history"
                ).fetchone()[0]
            )
