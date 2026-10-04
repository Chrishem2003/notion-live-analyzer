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

from nema_agora.access import can_read_observation, has_permission, require_permission
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
                    owner_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN (
                        'Received', 'Under review', 'Referred',
                        'Action recorded', 'Closed'
                    )),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS operation_events (\n                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,\n                    actor_id TEXT NOT NULL,\n                    operation TEXT NOT NULL,\n                    occurred_at TEXT NOT NULL,\n                    details_json TEXT NOT NULL DEFAULT '{}'\n                );\n\n                CREATE TABLE IF NOT EXISTS audit_events (
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

                CREATE TABLE IF NOT EXISTS intelligence_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL REFERENCES observations(case_id),
                    actor_id TEXT NOT NULL,
                    event_type TEXT NOT NULL CHECK (event_type IN (
                        'analysis_run', 'feedback_recorded'
                    )),
                    occurred_at TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_observations_status
                    ON observations(status);
                CREATE INDEX IF NOT EXISTS idx_observations_owner
                    ON observations(owner_id);
                CREATE INDEX IF NOT EXISTS idx_operation_time\n                    ON operation_events(occurred_at, event_id);\n                CREATE INDEX IF NOT EXISTS idx_audit_case_time
                    ON audit_events(case_id, occurred_at, event_id);
                CREATE INDEX IF NOT EXISTS idx_intelligence_case_time
                    ON intelligence_events(case_id, occurred_at, event_id);
                """
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(observations)")}
            if "owner_id" not in columns:
                # Legacy records have no trustworthy owner. Keep them inaccessible
                # to submitters; privileged reviewer/coordinator roles can review
                # and reassign them through an approved migration workflow.
                connection.execute(
                    "ALTER TABLE observations ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'legacy-unowned'"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_observations_owner ON observations(owner_id)"
            )

    def create_observation(self, record: dict[str, Any], *, actor_id: str, role: str) -> dict[str, Any]:
        actor = _actor(actor_id)
        require_permission(role, "observation:create")
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
        owner = str(stored.get("owner_id") or actor).strip()
        if not owner or len(owner) > 128:
            raise ValueError("A valid record owner identifier is required.")
        stored["owner_id"] = owner
        updated_at = str(stored.get("updated_at") or created_at)
        stored["updated_at"] = updated_at
        payload = json.dumps(stored, ensure_ascii=False, sort_keys=True)

        with self._session() as connection:
            connection.execute(
                """INSERT INTO observations
                   (case_id, status, owner_id, created_at, updated_at, record_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (case_id, status, owner, created_at, updated_at, payload),
            )
            connection.execute(
                """INSERT INTO audit_events
                   (case_id, actor_id, event_type, from_status, to_status,
                    occurred_at, details_json)
                   VALUES (?, ?, 'record_created', NULL, ?, ?, '{}')""",
                (case_id, actor, status, created_at),
            )
        return stored

    def get_observation(self, case_id: str, *, actor_id: str, role: str) -> dict[str, Any] | None:
        actor = _actor(actor_id)
        with self._session() as connection:
            row = connection.execute(
                "SELECT record_json, owner_id FROM observations WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        if not row:
            return None
        if not can_read_observation(role, actor, row["owner_id"]):
            raise PermissionError("You are not permitted to read this observation.")
        return json.loads(row["record_json"])

    def list_observations(self, *, actor_id: str, role: str, status: str | None = None) -> list[dict[str, Any]]:
        actor = _actor(actor_id)
        if status is not None and status not in STATUSES:
            raise ValueError("Unknown case status.")
        if has_permission(role, "observation:read_all"):
            query = "SELECT record_json FROM observations"
            parameters: tuple[str, ...] = ()
        else:
            require_permission(role, "observation:read_own")
            query = "SELECT record_json FROM observations WHERE owner_id = ?"
            parameters = (actor,)
        if status is not None:
            query += " AND status = ?" if " WHERE " in query else " WHERE status = ?"
            parameters += (status,)
        query += " ORDER BY created_at, case_id"
        with self._session() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [json.loads(row["record_json"]) for row in rows]

    def update_review(
        self,
        case_id: str,
        *,
        actor_id: str,
        role: str,
        new_status: str,
        review_notes: str,
        changed_at: str,
    ) -> dict[str, Any]:
        actor = _actor(actor_id)
        require_permission(role, "observation:review")
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

    def record_operation(self, *, actor_id: str, role: str, operation: str, occurred_at: str, details: dict[str, Any] | None = None) -> None:
        actor = _actor(actor_id)
        require_permission(role, "user:manage")
        operation = operation.strip()
        if not operation or len(operation) > 100:
            raise ValueError("A valid operation name is required.")
        if not occurred_at.strip():
            raise ValueError("An operation timestamp is required.")
        payload = json.dumps(details or {}, ensure_ascii=False, sort_keys=True)
        with self._session() as connection:
            connection.execute(
                "INSERT INTO operation_events (actor_id, operation, occurred_at, details_json) VALUES (?, ?, ?, ?)",
                (actor, operation, occurred_at, payload),
            )

    def list_operation_events(self, *, actor_id: str, role: str, limit: int = 100) -> list[dict[str, Any]]:
        _actor(actor_id)
        require_permission(role, "user:manage")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
            raise ValueError("Operation event limit must be between 1 and 500.")
        with self._session() as connection:
            rows = connection.execute(
                "SELECT event_id, actor_id, operation, occurred_at, details_json FROM operation_events ORDER BY event_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{**dict(row), "details": json.loads(row["details_json"])} for row in rows]

    def list_audit_events(self, case_id: str, *, actor_id: str, role: str) -> list[dict[str, Any]]:
        _actor(actor_id)
        require_permission(role, "audit:read")
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

    def record_intelligence_event(
        self, case_id: str, *, actor_id: str, role: str, event_type: str,
        occurred_at: str, details: dict[str, Any] | None = None,
    ) -> None:
        actor = _actor(actor_id)
        require_permission(role, "intelligence:use")
        if not case_id or len(case_id.strip()) > 64:
            raise ValueError("A valid case identifier is required.")
        if event_type not in {"analysis_run", "feedback_recorded"}:
            raise ValueError("Unknown intelligence event type.")
        if not occurred_at.strip():
            raise ValueError("An intelligence event timestamp is required.")
        payload = json.dumps(details or {}, ensure_ascii=False, sort_keys=True)
        with self._session() as connection:
            if connection.execute("SELECT 1 FROM observations WHERE case_id = ?", (case_id,)).fetchone() is None:
                raise KeyError(f"Case not found: {case_id}")
            connection.execute(
                "INSERT INTO intelligence_events (case_id, actor_id, event_type, occurred_at, details_json) VALUES (?, ?, ?, ?, ?)",
                (case_id, actor, event_type, occurred_at, payload),
            )

    def record_intelligence_feedback(
        self, case_id: str, *, actor_id: str, role: str,
        feedback: dict[str, Any], occurred_at: str,
    ) -> None:
        actor = _actor(actor_id)
        require_permission(role, "intelligence:feedback")
        if not case_id or len(case_id.strip()) > 64:
            raise ValueError("A valid case identifier is required.")
        if not occurred_at.strip():
            raise ValueError("A feedback timestamp is required.")
        feedback_type = str(feedback.get("feedback_type", "")).strip()
        if feedback_type not in {"accepted", "rejected", "corrected"}:
            raise ValueError("Feedback must be accepted, rejected, or corrected.")
        corrected_category = str(feedback.get("corrected_category", "")).strip()
        if feedback_type == "corrected" and not corrected_category:
            raise ValueError("Corrected feedback requires a corrected category.")
        if len(corrected_category) > 120:
            raise ValueError("Corrected category is too long.")
        notes = str(feedback.get("notes", "")).strip()
        if len(notes) > 1000:
            raise ValueError("Feedback notes must be 1000 characters or fewer.")
        payload = {
            "feedback_type": feedback_type,
            "corrected_category": corrected_category,
            "notes": notes,
            "copilot_version": str(feedback.get("copilot_version", "phase10-v1")).strip()[:50],
        }
        with self._session() as connection:
            if connection.execute("SELECT 1 FROM observations WHERE case_id = ?", (case_id,)).fetchone() is None:
                raise KeyError(f"Case not found: {case_id}")
            connection.execute(
                "INSERT INTO intelligence_events (case_id, actor_id, event_type, occurred_at, details_json) VALUES (?, ?, 'feedback_recorded', ?, ?)",
                (case_id, actor, occurred_at, json.dumps(payload, ensure_ascii=False, sort_keys=True)),
            )

    def list_intelligence_events(
        self, case_id: str, *, actor_id: str, role: str
    ) -> list[dict[str, Any]]:
        _actor(actor_id)
        require_permission(role, "audit:read")
        with self._session() as connection:
            rows = connection.execute(
                "SELECT event_id, case_id, actor_id, event_type, occurred_at, details_json FROM intelligence_events WHERE case_id = ? ORDER BY event_id",
                (case_id,),
            ).fetchall()
        return [{**dict(row), "details": json.loads(row["details_json"])} for row in rows]

