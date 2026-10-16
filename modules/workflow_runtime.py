"""Persistent single-process workflow runtime for registered, trusted handlers.

This is an executable foundation, not a distributed worker service. It stores task
payloads/results in SQLite, claims work transactionally, and records event history.
Only explicitly registered Python handlers can execute; user input never names imports.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from modules.workflow_contract import (
    SCHEMA_VERSION,
    WorkflowContractError,
    canonical_payload_digest,
    idempotency_key,
    validate_status_transition,
)
from modules.workflow_store import append_event_in_transaction, initialize_store

TaskHandler = Callable[[Mapping[str, Any]], Mapping[str, Any]]
MAX_INPUT_BYTES = 1_000_000
MAX_RESULT_BYTES = 1_000_000
_RUN_SCHEMA = """
CREATE TABLE IF NOT EXISTS workflow_runs (
    run_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    input_json TEXT NOT NULL,
    result_json TEXT,
    error_message TEXT,
    attempt INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    claimed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_queue
    ON workflow_runs(status, created_at);
"""


class HandlerNotRegistered(WorkflowContractError):
    """The requested task type has no explicitly registered trusted handler."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect(database: str | Path) -> sqlite3.Connection:
    path = str(database)
    if path != ":memory:":
        Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def _initialize(database: str | Path) -> None:
    initialize_store(database)
    with closing(_connect(database)) as connection:
        connection.executescript(_RUN_SCHEMA)


def _event_payload(*, workflow_id: str, run_id: str, task_type: str, stage: str,
                   status: str, payload: Mapping[str, Any],
                   evidence_refs: tuple[str, ...] = ()) -> dict[str, Any]:
    digest = canonical_payload_digest(payload)
    event_type = f"{task_type}.{status}"
    key = idempotency_key(workflow_id, run_id, event_type, digest)
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "idempotency_key": key,
        "workflow_id": workflow_id,
        "run_id": run_id,
        "event_type": event_type,
        "stage": stage,
        "status": status,
        "occurred_at": _utc_now(),
        "payload_digest": digest,
        "evidence_refs": list(evidence_refs),
    }

class WorkflowRuntime:
    """Durable local task queue with an explicit allow-list of callable handlers."""

    def __init__(self, database: str | Path, *, handlers: Mapping[str, TaskHandler] | None = None):
        self.database = str(database)
        self.handlers: dict[str, TaskHandler] = {}
        _initialize(self.database)
        for task_type, handler in (handlers or {}).items():
            self.register_handler(task_type, handler)

    def register_handler(self, task_type: str, handler: TaskHandler) -> None:
        if not isinstance(task_type, str) or not task_type.strip():
            raise ValueError("task_type must be a non-empty string")
        if not callable(handler):
            raise TypeError("handler must be callable")
        self.handlers[task_type.strip()] = handler

    def submit(self, *, workflow_id: str, task_type: str,
               payload: Mapping[str, Any], max_attempts: int = 3) -> str:
        if not isinstance(workflow_id, str) or not workflow_id.strip():
            raise ValueError("workflow_id must be a non-empty string")
        if task_type not in self.handlers:
            raise HandlerNotRegistered(f"no trusted handler registered for task type {task_type!r}")
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a mapping")
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1 or max_attempts > 10:
            raise ValueError("max_attempts must be an integer between 1 and 10")
        try:
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("payload must contain finite JSON-compatible values") from exc
        if len(encoded.encode("utf-8")) > MAX_INPUT_BYTES:
            raise ValueError(f"payload exceeds the {MAX_INPUT_BYTES}-byte runtime limit")
        run_id = str(uuid.uuid4())
        now = _utc_now()
        with closing(_connect(self.database)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """INSERT INTO workflow_runs
                    (run_id, workflow_id, task_type, status, input_json, attempt,
                     max_attempts, created_at, updated_at)
                    VALUES (?, ?, ?, 'queued', ?, 0, ?, ?, ?)""",
                    (run_id, workflow_id.strip(), task_type, encoded, max_attempts, now, now),
                )
                append_event_in_transaction(
                    connection,
                    _event_payload(
                        workflow_id=workflow_id.strip(), run_id=run_id,
                        task_type=task_type, stage="problem_solving", status="queued",
                        payload={"input": json.loads(encoded), "attempt": 0},
                    ),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
        return run_id

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with closing(_connect(self.database)) as connection:
            row = connection.execute("SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["input"] = json.loads(result.pop("input_json"))
        raw_result = result.pop("result_json")
        result["result"] = json.loads(raw_result) if raw_result else None
        return result

    def list_runs(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        with closing(_connect(self.database)) as connection:
            rows = connection.execute(
                "SELECT run_id FROM workflow_runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self.get_run(row["run_id"]) for row in rows if row is not None]

    def execute_next(self) -> dict[str, Any] | None:
        """Execute the oldest queued run, without duplicating execution logic."""
        with closing(_connect(self.database)) as connection:
            row = connection.execute(
                "SELECT run_id FROM workflow_runs WHERE status = 'queued' ORDER BY created_at, rowid LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return self.execute_run(row["run_id"])

    def execute_run(self, run_id: str) -> dict[str, Any] | None:
        """Execute one specific queued run; leave unrelated queue items untouched."""
        with closing(_connect(self.database)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT * FROM workflow_runs WHERE run_id = ? AND status = 'queued'",
                    (run_id,),
                ).fetchone()
                if row is None:
                    connection.execute("COMMIT")
                    return self.get_run(run_id)
                now = _utc_now()
                attempt = int(row["attempt"]) + 1
                validate_status_transition("queued", "running")
                connection.execute(
                    "UPDATE workflow_runs SET status='running', attempt=?, claimed_at=?, updated_at=? WHERE run_id=? AND status='queued'",
                    (attempt, now, now, run_id),
                )
                append_event_in_transaction(
                    connection,
                    _event_payload(
                        workflow_id=row["workflow_id"], run_id=run_id,
                        task_type=row["task_type"], stage="problem_solving", status="running",
                        payload={"attempt": attempt, "input_digest": canonical_payload_digest(json.loads(row["input_json"]))},
                    ),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

        workflow_id, task_type = row["workflow_id"], row["task_type"]
        payload = json.loads(row["input_json"])
        handler = self.handlers.get(task_type)
        try:
            if handler is None:
                raise HandlerNotRegistered(f"handler {task_type!r} is not registered in this worker")
            result = handler(payload)
            if not isinstance(result, Mapping):
                raise TypeError("workflow handler must return a mapping")
            encoded_result = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            if len(encoded_result.encode("utf-8")) > MAX_RESULT_BYTES:
                raise ValueError(f"handler result exceeds the {MAX_RESULT_BYTES}-byte runtime limit")
            outcome = "succeeded"
            error_message = None
        except Exception as exc:
            encoded_result = None
            error_message = f"{type(exc).__name__}: {str(exc)[:500]}"
            outcome = "queued" if attempt < int(row["max_attempts"]) else "failed"

        now = _utc_now()
        with closing(_connect(self.database)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    "UPDATE workflow_runs SET status=?, result_json=?, error_message=?, updated_at=? WHERE run_id=? AND status='running'",
                    (outcome, encoded_result, error_message, now, run_id),
                )
                outcome_payload = (
                    {"result": json.loads(encoded_result)} if encoded_result else
                    {"attempt": attempt, "error": error_message, "retry_scheduled": outcome == "queued"}
                )
                append_event_in_transaction(
                    connection,
                    _event_payload(
                        workflow_id=workflow_id, run_id=run_id, task_type=task_type,
                        stage="problem_solving", status=outcome, payload=outcome_payload,
                    ),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
        return self.get_run(run_id)

    def recover_stale_runs(self, *, older_than_seconds: int = 600) -> list[dict[str, Any]]:
        """Recover runs left in 'running' after a process interruption.

        This is an explicit maintenance operation for a single-process/local runtime.
        Do not run it concurrently with long-lived workers unless the deployment has
        real worker leases and heartbeat updates.
        """
        if isinstance(older_than_seconds, bool) or not isinstance(older_than_seconds, int) or older_than_seconds < 1:
            raise ValueError("older_than_seconds must be a positive integer")
        now_dt = datetime.now(timezone.utc)
        cutoff = now_dt.timestamp() - older_than_seconds
        recovered: list[dict[str, Any]] = []
        with closing(_connect(self.database)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                rows = connection.execute(
                    "SELECT * FROM workflow_runs WHERE status='running' AND claimed_at IS NOT NULL"
                ).fetchall()
                for row in rows:
                    try:
                        claimed = datetime.fromisoformat(row["claimed_at"].replace("Z", "+00:00"))
                    except (TypeError, ValueError):
                        continue
                    if claimed.tzinfo is None or claimed.timestamp() > cutoff:
                        continue
                    attempt = int(row["attempt"])
                    outcome = "queued" if attempt < int(row["max_attempts"]) else "failed"
                    validate_status_transition("running", outcome)
                    error = "Recovered stale running state after worker interruption."
                    updated = now_dt.isoformat(timespec="seconds")
                    connection.execute(
                        "UPDATE workflow_runs SET status=?, error_message=?, updated_at=?, claimed_at=NULL WHERE run_id=? AND status='running'",
                        (outcome, error, updated, row["run_id"]),
                    )
                    append_event_in_transaction(
                        connection,
                        _event_payload(
                            workflow_id=row["workflow_id"], run_id=row["run_id"],
                            task_type=row["task_type"], stage="problem_solving",
                            status=outcome,
                            payload={
                                "recovered": True,
                                "previous_attempt": attempt,
                                "error": error,
                                "retry_scheduled": outcome == "queued",
                            },
                        ),
                    )
                    recovered.append({"run_id": row["run_id"], "status": outcome, "attempt": attempt})
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
        return recovered
