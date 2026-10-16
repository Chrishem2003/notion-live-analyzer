"""SQLite-backed append-only workflow event store.

This is a local durable adapter, not a distributed queue or a Notion sync client.
Use a persistent writable path, protect the database file, and back it up operationally.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from modules.workflow_contract import WorkflowContractError, WorkflowEvent


_SCHEMA = """
CREATE TABLE IF NOT EXISTS workflow_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    idempotency_key TEXT NOT NULL UNIQUE,
    workflow_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    payload_digest TEXT NOT NULL,
    event_json TEXT NOT NULL,
    stored_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_workflow_events_run
    ON workflow_events(workflow_id, run_id, sequence);
CREATE INDEX IF NOT EXISTS idx_workflow_events_status
    ON workflow_events(status, sequence);
"""


class IdempotencyConflict(WorkflowContractError):
    """A previously used idempotency key was presented with different content."""


def _connect(database: str | Path) -> sqlite3.Connection:
    path = str(database)
    if path != ":memory:":
        Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_store(database: str | Path) -> None:
    """Create the event table/indexes idempotently without deleting existing records."""
    with _connect(database) as connection:
        connection.executescript(_SCHEMA)


def append_event(database: str | Path, raw_event: WorkflowEvent | Mapping[str, Any]) -> bool:
    """Atomically append an event.

    Returns True when inserted and False when an identical idempotency key/payload
    has already been accepted. Reusing a key for a different digest raises a conflict.
    """
    event = raw_event if isinstance(raw_event, WorkflowEvent) else WorkflowEvent.from_mapping(raw_event)
    payload = event.to_dict()
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    with _connect(database) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            existing = connection.execute(
                "SELECT payload_digest, event_type, workflow_id, run_id "
                "FROM workflow_events WHERE idempotency_key = ?",
                (event.idempotency_key,),
            ).fetchone()
            if existing is not None:
                if (
                    existing["payload_digest"] == event.payload_digest
                    and existing["event_type"] == event.event_type
                    and existing["workflow_id"] == event.workflow_id
                    and existing["run_id"] == event.run_id
                ):
                    connection.execute("COMMIT")
                    return False
                raise IdempotencyConflict(
                    "idempotency key already exists with different event identity or payload"
                )
            connection.execute(
                """
                INSERT INTO workflow_events (
                    event_id, idempotency_key, workflow_id, run_id, event_type,
                    stage, status, occurred_at, payload_digest, event_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id, event.idempotency_key, event.workflow_id,
                    event.run_id, event.event_type, event.stage, event.status,
                    event.occurred_at, event.payload_digest, encoded,
                ),
            )
            connection.execute("COMMIT")
            return True
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise


def list_run_events(database: str | Path, workflow_id: str, run_id: str) -> list[dict[str, Any]]:
    """Return an ordered snapshot for a run; no update/delete interface is exposed."""
    with _connect(database) as connection:
        rows = connection.execute(
            """
            SELECT sequence, event_id, idempotency_key, event_type, stage, status,
                   occurred_at, payload_digest, event_json, stored_at
            FROM workflow_events
            WHERE workflow_id = ? AND run_id = ?
            ORDER BY sequence ASC
            """,
            (workflow_id, run_id),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["event"] = json.loads(item.pop("event_json"))
        result.append(item)
    return result
