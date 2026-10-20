"""Persistent idempotency ledger for research-run write-back.

Use a database file on persistent storage shared by every API worker that can
accept research-run requests. SQLite's BEGIN IMMEDIATE serializes reservations
among processes using the same file. Do not use an ephemeral per-container path
for a multi-replica deployment.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import closing
from typing import Any, Dict


class IdempotencyConflictError(RuntimeError):
    """A run ID was reused with a different request payload."""


class RunIdempotencyLedger:
    def __init__(self, database_path: str) -> None:
        if not isinstance(database_path, str) or not database_path.strip():
            raise ValueError("A persistent idempotency database path is required.")
        self.database_path = os.path.abspath(database_path)
        parent = os.path.dirname(self.database_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS research_run_idempotency (
                    run_id TEXT PRIMARY KEY,
                    payload_hash TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (state IN
                        ('pending', 'complete', 'ambiguous', 'failed')),
                    notion_page_id TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=15, isolation_level=None)
        connection.execute("PRAGMA busy_timeout = 15000")
        return connection

    @staticmethod
    def fingerprint(payload: Dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def reserve(self, run_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be a non-empty stable string.")
        stable_id = run_id.strip()
        payload_hash = self.fingerprint(payload)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_hash, state, notion_page_id, updated_at "
                "FROM research_run_idempotency WHERE run_id = ?",
                (stable_id,),
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO research_run_idempotency "
                    "(run_id, payload_hash, state) VALUES (?, ?, 'pending')",
                    (stable_id, payload_hash),
                )
                connection.execute("COMMIT")
                return {"action": "reserved", "page_id": None}
            existing_hash, state, page_id, updated_at = row
            if existing_hash != payload_hash:
                raise IdempotencyConflictError(
                    "This run_id was already reserved with a different payload. "
                    "Use the original payload or a new run_id."
                )
            if state == "pending":
                stale = connection.execute(
                    "SELECT datetime(?) < datetime('now', '-5 minutes')",
                    (updated_at,),
                ).fetchone()[0]
                if stale:
                    connection.execute(
                        "UPDATE research_run_idempotency SET state='ambiguous', "
                        "updated_at=CURRENT_TIMESTAMP WHERE run_id=?",
                        (stable_id,),
                    )
                    state = "ambiguous"
            if state == "failed":
                connection.execute(
                    "UPDATE research_run_idempotency SET state='pending', "
                    "updated_at=CURRENT_TIMESTAMP WHERE run_id=?",
                    (stable_id,),
                )
                connection.execute("COMMIT")
                return {"action": "reserved", "page_id": None}
            connection.execute("COMMIT")
            if state == "complete":
                return {"action": "complete", "page_id": page_id}
            if state == "ambiguous":
                return {"action": "recover", "page_id": page_id}
            return {"action": "in_progress", "page_id": None}
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def mark_complete(self, run_id: str, page_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE research_run_idempotency SET state='complete', notion_page_id=?, "
                "updated_at=CURRENT_TIMESTAMP WHERE run_id=?",
                (page_id, run_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Cannot complete an unreserved run_id.")

    def mark_ambiguous(self, run_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE research_run_idempotency SET state='ambiguous', "
                "updated_at=CURRENT_TIMESTAMP WHERE run_id=?",
                (run_id,),
            )

    def mark_failed(self, run_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE research_run_idempotency SET state='failed', "
                "updated_at=CURRENT_TIMESTAMP WHERE run_id=?",
                (run_id,),
            )
