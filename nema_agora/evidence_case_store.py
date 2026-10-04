"""Append-only persistence for governed NEMA-AGORA evidence cases and transitions."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .evidence_case import EvidenceCase, validate_evidence_case


class EvidenceCaseStore:
    """SQLite append-only case store; historical transitions are events, never updates."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS evidence_cases (
                    case_id TEXT PRIMARY KEY,
                    provenance_fingerprint TEXT UNIQUE NOT NULL,
                    state TEXT NOT NULL,
                    case_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    stored_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS evidence_case_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    state TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_evidence_case_events_case
                    ON evidence_case_events(case_id, event_id);
                CREATE TRIGGER IF NOT EXISTS evidence_cases_no_update
                BEFORE UPDATE ON evidence_cases
                BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;
                CREATE TRIGGER IF NOT EXISTS evidence_cases_no_delete
                BEFORE DELETE ON evidence_cases
                BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;
                CREATE TRIGGER IF NOT EXISTS evidence_case_events_no_update
                BEFORE UPDATE ON evidence_case_events
                BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;
                CREATE TRIGGER IF NOT EXISTS evidence_case_events_no_delete
                BEFORE DELETE ON evidence_case_events
                BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;
                """
            )

    def append(self, case: EvidenceCase) -> None:
        validation = validate_evidence_case(case)
        if not validation["valid"]:
            raise ValueError(f"invalid evidence case: {validation['issues']}")
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO evidence_cases
                   (case_id, provenance_fingerprint, state, case_json, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (case.case_id, case.provenance_fingerprint, case.state,
                 json.dumps(case.to_dict(), sort_keys=True, ensure_ascii=False),
                 case.created_at),
            )

    def get(self, case_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT case_id, provenance_fingerprint, state, case_json, created_at, stored_at "
                "FROM evidence_cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        return dict(row) if row else None

    def list(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT case_id, provenance_fingerprint, state, case_json, created_at, stored_at "
                "FROM evidence_cases ORDER BY stored_at, case_id"
            ).fetchall()
        return [dict(row) for row in rows]

    def count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM evidence_cases").fetchone()[0])

    def append_event(
        self,
        *,
        case_id: str,
        event_type: str,
        state: str,
        actor_id: str,
        role: str,
        event: dict[str, Any],
        created_at: str,
    ) -> int:
        if not all(value.strip() for value in (case_id, event_type, state, actor_id, role, created_at)):
            raise ValueError("event identity fields are required")
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO evidence_case_events
                   (case_id, event_type, state, actor_id, role, event_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (case_id, event_type, state, actor_id, role,
                 json.dumps(event, sort_keys=True, ensure_ascii=False), created_at),
            )
            return int(cur.lastrowid)

    def list_events(self, case_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT event_id, case_id, event_type, state, actor_id, role,
                          event_json, created_at
                   FROM evidence_case_events WHERE case_id = ? ORDER BY event_id""",
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]
