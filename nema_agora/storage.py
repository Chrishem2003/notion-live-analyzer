"""SQLite persistence layer for NEMA-AGORA.

This module is intentionally not wired into the public Streamlit page yet.
Only call it behind authenticated identity, role checks, deployment-specific
secret/configuration, and an approved retention/backup policy.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from nema_agora.core import STATUSES
from nema_agora.workflow import apply_status_update


def _actor(value: str) -> str:
    actor = (value or "").strip()
    if not actor:
        raise ValueError("An authenticated actor identifier is required.")
    if len(actor) > 128:
        raise ValueError("Actor identifier must be 128 characters or fewer.")
    return actor


class NemaAgoraRepository:
    """Small SQLite repository with transactional status changes and audit events."""

    def __init__(self, database_path: str | Path):
        path = str(database_path)
        if not path.strip():
            raise ValueError("An explicit database path is required.")
        self.database_path = path
        self._initialise()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            if connection.in_transaction:
                connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _initialise(self) -> None:
        with self._session() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS observations (
                    case_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL CHECK (status IN (
                        'Received', 'Under review', 'Referred',
                        'Action recorded', 'Closed'
                    )),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL REFERENCES observations(case_id),
                    actor_id TEXT NOT NULL,
                    event_type TEXT NOT NULL CHECK (event_type IN (
                        'record_created', 'status_changed', 'review_updated'
                    )),
                    from_status TEXT,
                    to_status TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_observations_status
                    ON observations(status);
                CREATE INDEX IF NOT EXISTS idx_audit_case_time
                    ON audit_events(case_id, occurred_at, event_id);
                """
            )

    def create_observation(self, record: dict[str, Any], *, actor_id: str) -> dict[str, Any]:
        actor = _actor(actor_id)
        case_id = str(record.get("case_id", "")).strip()
        status = record.get("status")
        created_at = str(record.get("created_at", "")).strip()
        if not case_id or len(case_id) > 64:
            raise ValueError("A valid case identifier is required.")
        if status not in STATUSES:
            raise ValueError("A valid initial status is required.")
        if not created_at:
            raise ValueError("A creation timestamp is required.")

        stored = dict(record)
        updated_at = str(stored.get("updated_at") or created_at)
        stored["updated_at"] = updated_at
        payload = json.dumps(stored, ensure_ascii=False, sort_keys=True)

        with self._session() as connection:
            connection.execute(
                """INSERT INTO observations
                   (case_id, status, created_at, updated_at, record_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (case_id, status, created_at, updated_at, payload),
            )
            connection.execute(
                """INSERT INTO audit_events
                   (case_id, actor_id, event_type, from_status, to_status,
                    occurred_at, details_json)
                   VALUES (?, ?, 'record_created', NULL, ?, ?, '{}')""",
                (case_id, actor, status, created_at),
            )
        return stored

    def get_observation(self, case_id: str) -> dict[str, Any] | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT record_json FROM observations WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        return json.loads(row["record_json"]) if row else None

    def list_observations(self, *, status: str | None = None) -> list[dict[str, Any]]:
        if status is not None and status not in STATUSES:
            raise ValueError("Unknown case status.")
        query = "SELECT record_json FROM observations"
        parameters: tuple[str, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            parameters = (status,)
        query += " ORDER BY created_at, case_id"
        with self._session() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [json.loads(row["record_json"]) for row in rows]

    def update_review(
        self,
        case_id: str,
        *,
        actor_id: str,
        new_status: str,
        review_notes: str,
        changed_at: str,
    ) -> dict[str, Any]:
        actor = _actor(actor_id)
        if not changed_at or not changed_at.strip():
            raise ValueError("A change timestamp is required.")

        with self._session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT record_json FROM observations WHERE case_id = ?",
                (case_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Case not found: {case_id}")
            current = json.loads(row["record_json"])
            updated, event = apply_status_update(
                current,
                new_status=new_status,
                review_notes=review_notes,
                changed_at=changed_at,
            )
            connection.execute(
                """UPDATE observations
                   SET status = ?, updated_at = ?, record_json = ?
                   WHERE case_id = ?""",
                (
                    updated["status"],
                    updated["updated_at"],
                    json.dumps(updated, ensure_ascii=False, sort_keys=True),
                    case_id,
                ),
            )
            connection.execute(
                """INSERT INTO audit_events
                   (case_id, actor_id, event_type, from_status, to_status,
                    occurred_at, details_json)
                   VALUES (?, ?, ?, ?, ?, ?, '{}')""",
                (
                    case_id,
                    actor,
                    "status_changed" if event else "review_updated",
                    current["status"] if event else None,
                    updated["status"],
                    changed_at,
                ),
            )
        return updated

    def list_audit_events(self, case_id: str) -> list[dict[str, Any]]:
        with self._session() as connection:
            rows = connection.execute(
                """SELECT event_id, case_id, actor_id, event_type, from_status,
                          to_status, occurred_at, details_json
                   FROM audit_events
                   WHERE case_id = ?
                   ORDER BY event_id""",
                (case_id,),
            ).fetchall()
        return [
            {
                **dict(row),
                "details": json.loads(row["details_json"]),
            }
            for row in rows
        ]
