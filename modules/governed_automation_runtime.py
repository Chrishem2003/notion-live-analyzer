"""Governed synchronous automation runtime; no scheduler or implicit integrations.

Workflows must be explicitly registered, caller authorization must succeed, and
input/output values are bounded JSON. Retries are allowed only for handlers
explicitly declared idempotent. This module does not create background jobs.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

MAX_INPUT_BYTES = 65_536
MAX_OUTPUT_BYTES = 262_144
_NAME_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,99}$")


class AutomationAuthorizationError(PermissionError):
    pass


class AutomationConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkflowSpec:
    name: str
    handler: Callable[[dict[str, Any]], Any]
    validate_input: Callable[[dict[str, Any]], None]
    idempotent: bool = False
    max_attempts: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _NAME_RE.fullmatch(self.name):
            raise ValueError("Workflow name must be a stable lowercase identifier.")
        if not callable(self.handler) or not callable(self.validate_input):
            raise ValueError("Workflow handler and input validator must be callable.")
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int):
            raise ValueError("max_attempts must be an integer.")
        if not 1 <= self.max_attempts <= 3:
            raise ValueError("max_attempts must be between 1 and 3.")
        if not self.idempotent and self.max_attempts != 1:
            raise ValueError("Non-idempotent workflows must use exactly one attempt.")


def _json_bytes(value: Any, *, limit: int, label: str) -> tuple[str, str]:
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be finite JSON-compatible data.") from exc
    if len(encoded.encode("utf-8")) > limit:
        raise ValueError(f"{label} exceeds the {limit}-byte limit.")
    return encoded, hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class GovernedAutomationRuntime:
    """Run allow-listed workflows with idempotency, authorization and audit events.

    An authorization callback from the hosting application's trusted auth layer
    is required. Actor values are metadata, not authentication. File-backed SQLite
    is durable only when the host guarantees that path.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        authorize: Callable[[str, str], bool] | None,
    ) -> None:
        path = str(database_path)
        if not path.strip():
            raise ValueError("A database path is required.")
        if path != ":memory:" and not path.startswith("file:"):
            Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._authorize = authorize
        self._workflows: dict[str, WorkflowSpec] = {}
        self._lock = threading.RLock()
        self._db = sqlite3.connect(
            path, timeout=5, isolation_level=None, check_same_thread=False
        )
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.execute("PRAGMA busy_timeout = 5000")
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS automation_jobs (
                job_id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                workflow_name TEXT NOT NULL,
                input_hash TEXT NOT NULL,
                input_json TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('running','succeeded','failed')),
                actor TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                output_json TEXT,
                error_code TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS automation_audit (
                audit_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL REFERENCES automation_jobs(job_id),
                event_type TEXT NOT NULL,
                event_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_automation_audit_job_created
                ON automation_audit(job_id, created_at, audit_id);
            CREATE TRIGGER IF NOT EXISTS automation_audit_no_update
            BEFORE UPDATE ON automation_audit BEGIN
                SELECT RAISE(ABORT, 'automation audit events are append-only');
            END;
            CREATE TRIGGER IF NOT EXISTS automation_audit_no_delete
            BEFORE DELETE ON automation_audit BEGIN
                SELECT RAISE(ABORT, 'automation audit events are append-only');
            END;
            """
        )

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def __enter__(self) -> "GovernedAutomationRuntime":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    def register(self, spec: WorkflowSpec) -> None:
        if not isinstance(spec, WorkflowSpec):
            raise TypeError("Only WorkflowSpec instances may be registered.")
        with self._lock:
            if spec.name in self._workflows:
                raise ValueError(f"Workflow already registered: {spec.name}")
            self._workflows[spec.name] = spec

    def execute(
        self,
        workflow_name: str,
        inputs: Mapping[str, Any],
        *,
        actor: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if not isinstance(actor, str) or not actor.strip() or len(actor.strip()) > 120:
            raise ValueError("A bounded actor identifier is required.")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key.strip()) > 200:
            raise ValueError("A bounded idempotency key is required.")
        with self._lock:
            spec = self._workflows.get(workflow_name)
        if spec is None:
            raise KeyError(f"Workflow is not registered: {workflow_name}")
        if self._authorize is None or self._authorize(actor.strip(), workflow_name) is not True:
            raise AutomationAuthorizationError("Workflow execution is not authorized.")
        if not isinstance(inputs, Mapping):
            raise ValueError("Workflow inputs must be a JSON object.")
        input_json, input_hash = _json_bytes(dict(inputs), limit=MAX_INPUT_BYTES, label="Workflow input")
        validated_inputs = json.loads(input_json)
        spec.validate_input(validated_inputs)

        now = _timestamp()
        job_id = uuid.uuid4().hex
        with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                existing = self._db.execute(
                    "SELECT * FROM automation_jobs WHERE idempotency_key = ?",
                    (idempotency_key.strip(),),
                ).fetchone()
                if existing is not None:
                    self._db.execute("COMMIT")
                    if existing["workflow_name"] != workflow_name or existing["input_hash"] != input_hash:
                        raise AutomationConflictError("Idempotency key was already used for different workflow inputs.")
                    if existing["status"] == "running":
                        raise AutomationConflictError("This idempotency key is already running.")
                    return self._public_job(existing, replayed=True)
                self._db.execute(
                    """INSERT INTO automation_jobs
                    (job_id,idempotency_key,workflow_name,input_hash,input_json,status,actor,attempts,created_at,updated_at)
                    VALUES (?,?,?,?,?,'running',?,0,?,?)""",
                    (job_id, idempotency_key.strip(), workflow_name, input_hash, input_json, actor.strip(), now, now),
                )
                self._audit(job_id, "job_started", {
                    "job_id": job_id, "workflow_name": workflow_name, "actor": actor.strip(),
                    "input_hash": input_hash, "status": "running",
                }, now)
                self._db.execute("COMMIT")
            except sqlite3.IntegrityError as exc:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise AutomationConflictError("Idempotency key reservation conflicted; read job status before retrying.") from exc
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

        output_json = None
        error_code = None
        attempts = 0
        for attempt in range(1, spec.max_attempts + 1):
            attempts = attempt
            try:
                output = spec.handler(dict(validated_inputs))
                output_json, _ = _json_bytes(output, limit=MAX_OUTPUT_BYTES, label="Workflow output")
                break
            except Exception as exc:
                error_code = type(exc).__name__[:120]
                if attempt >= spec.max_attempts:
                    break
        status_value = "succeeded" if output_json is not None and error_code is None else "failed"
        now = _timestamp()
        with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                self._db.execute(
                    "UPDATE automation_jobs SET status=?, attempts=?, output_json=?, error_code=?, updated_at=? WHERE job_id=? AND status='running'",
                    (status_value, attempts, output_json, error_code, now, job_id),
                )
                self._audit(job_id, "job_" + status_value, {
                    "job_id": job_id, "workflow_name": workflow_name, "status": status_value,
                    "attempts": attempts, "error_code": error_code,
                }, now)
                self._db.execute("COMMIT")
                row = self._db.execute("SELECT * FROM automation_jobs WHERE job_id=?", (job_id,)).fetchone()
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise
        return self._public_job(row, replayed=False)

    def get_job(self, job_id: str, *, actor: str) -> dict[str, Any] | None:
        if self._authorize is None:
            raise AutomationAuthorizationError("Job access is not authorized.")
        with self._lock:
            row = self._db.execute("SELECT * FROM automation_jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            return None
        if self._authorize(actor, row["workflow_name"]) is not True:
            raise AutomationAuthorizationError("Job access is not authorized.")
        return self._public_job(row, replayed=False)

    def list_audit(self, job_id: str, *, actor: str, limit: int = 100) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("Audit limit must be between 1 and 1000.")
        job = self.get_job(job_id, actor=actor)
        if job is None:
            return []
        with self._lock:
            rows = self._db.execute(
                "SELECT event_json FROM automation_audit WHERE job_id=? ORDER BY created_at, audit_id LIMIT ?",
                (job_id, limit),
            ).fetchall()
        return [json.loads(row["event_json"]) for row in rows]

    def _audit(self, job_id: str, event_type: str, event: dict[str, Any], timestamp: str) -> None:
        audit_id = uuid.uuid4().hex
        payload = {**event, "audit_id": audit_id, "event_type": event_type, "created_at": timestamp}
        encoded, _ = _json_bytes(payload, limit=MAX_INPUT_BYTES, label="Automation audit event")
        self._db.execute(
            "INSERT INTO automation_audit(audit_id,job_id,event_type,event_json,created_at) VALUES(?,?,?,?,?)",
            (audit_id, job_id, event_type, encoded, timestamp),
        )

    @staticmethod
    def _public_job(row: sqlite3.Row, *, replayed: bool) -> dict[str, Any]:
        return {
            "job_id": row["job_id"],
            "workflow_name": row["workflow_name"],
            "status": row["status"],
            "attempts": int(row["attempts"]),
            "output": json.loads(row["output_json"]) if row["output_json"] else None,
            "error_code": row["error_code"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "replayed": replayed,
        }
