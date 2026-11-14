"""SQLite-backed append-only workflow event store.

This is a local durable adapter, not a distributed queue or a Notion sync client.
Use a persistent writable path, protect the database file, and back it up operationally.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
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


def _decode_stored_event(existing: sqlite3.Row) -> WorkflowEvent:
    """Validate stored JSON and its indexed columns before trusting an event."""
    try:
        raw = json.loads(existing["event_json"])
    except (TypeError, ValueError) as exc:
        raise IdempotencyConflict(
            "stored event JSON cannot be decoded"
        ) from exc
    if not isinstance(raw, dict):
        raise IdempotencyConflict("stored event JSON must be an object")
    try:
        stored = WorkflowEvent.from_mapping(raw)
    except WorkflowContractError as exc:
        raise IdempotencyConflict(
            "stored event JSON does not satisfy the workflow event contract"
        ) from exc
    if stored.to_dict() != raw:
        raise IdempotencyConflict("stored event JSON is not in canonical contract form")
    indexed = {
        "event_id": stored.event_id,
        "idempotency_key": stored.idempotency_key,
        "workflow_id": stored.workflow_id,
        "run_id": stored.run_id,
        "event_type": stored.event_type,
        "stage": stored.stage,
        "status": stored.status,
        "occurred_at": stored.occurred_at,
        "payload_digest": stored.payload_digest,
    }
    if any(existing[column] != value for column, value in indexed.items()):
        raise IdempotencyConflict(
            "stored event JSON does not match its indexed columns"
        )
    return stored


def _same_logical_event(existing: sqlite3.Row, event: WorkflowEvent) -> bool:
    """Compare immutable event identity fields for an idempotent replay."""
    stored = _decode_stored_event(existing)
    return (
        stored.payload_digest == event.payload_digest
        and stored.event_type == event.event_type
        and stored.workflow_id == event.workflow_id
        and stored.run_id == event.run_id
        and stored.stage == event.stage
        and stored.status == event.status
        and stored.evidence_refs == event.evidence_refs
    )


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
    with closing(_connect(database)) as connection:
        connection.executescript(_SCHEMA)


def append_event(database: str | Path, raw_event: WorkflowEvent | Mapping[str, Any]) -> bool:
    """Atomically append an event.

    Returns True when inserted and False when an identical idempotency key/payload
    has already been accepted. Reusing a key for a different digest raises a conflict.
    """
    event = raw_event if isinstance(raw_event, WorkflowEvent) else WorkflowEvent.from_mapping(raw_event)
    payload = event.to_dict()
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    with closing(_connect(database)) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            existing = connection.execute(
                "SELECT event_id, idempotency_key, workflow_id, run_id, event_type, "
                "stage, status, occurred_at, payload_digest, event_json "
                "FROM workflow_events WHERE idempotency_key = ?",
                (event.idempotency_key,),
            ).fetchone()
            if existing is not None:
                if _same_logical_event(existing, event):
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
    with closing(_connect(database)) as connection:
        rows = connection.execute(
            """
            SELECT sequence, event_id, idempotency_key, workflow_id, run_id,
                   event_type, stage, status, occurred_at, payload_digest,
                   event_json, stored_at
            FROM workflow_events
            WHERE workflow_id = ? AND run_id = ?
            ORDER BY sequence ASC
            """,
            (workflow_id, run_id),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item.pop("event_json")
        item["event"] = _decode_stored_event(row).to_dict()
        result.append(item)
    return result


def append_event_in_transaction(connection: sqlite3.Connection, raw_event: WorkflowEvent | Mapping[str, Any]) -> bool:
    """Append using a caller-owned transaction so state and event commit together."""
    event = raw_event if isinstance(raw_event, WorkflowEvent) else WorkflowEvent.from_mapping(raw_event)
    payload = event.to_dict()
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    existing = connection.execute(
        "SELECT event_id, idempotency_key, workflow_id, run_id, event_type, "
                "stage, status, occurred_at, payload_digest, event_json "
        "FROM workflow_events WHERE idempotency_key = ?",
        (event.idempotency_key,),
    ).fetchone()
    if existing is not None:
        if _same_logical_event(existing, event):
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
    return True
