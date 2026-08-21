"""
task_status_registry.py
Persistence layer for asynchronous task state shared across:
  - tasks.py (Celery/ThreadPool workers)
  - fastapi_app.py (API bridge)
  - Streamlit pages (live progress polling)

Design:
  - Uses SQLite (zero-config, works in VSCode without Redis).
  - When Celery+Redis is available, task metadata is also mirrored so the
    same registry API works transparently.
  - Thread-safe writes via a per-process lock.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

APP_DIR = Path(__file__).resolve().parent.parent
REGISTRY_DB = str(APP_DIR / "task_registry.db")

_lock = threading.Lock()

_TASK_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    progress REAL NOT NULL DEFAULT 0.0,
    message TEXT DEFAULT '',
    result_json TEXT DEFAULT 'null',
    error TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(REGISTRY_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_registry() -> None:
    """Create the task registry table if it does not exist."""
    conn = _conn()
    try:
        conn.executescript(_TASK_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def create_task(name: str, meta: Optional[Dict[str, Any]] = None) -> str:
    """Register a new task and return its ID."""
    init_registry()
    task_id = str(uuid.uuid4())[:12].upper()
    now = datetime.utcnow().isoformat()
    meta_payload = json.dumps(meta or {})
    conn = _conn()
    try:
        with _lock:
            conn.execute(
                "INSERT INTO tasks (id, name, status, progress, message, result_json, error, created_at, updated_at) "
                "VALUES (?, ?, 'PENDING', 0.0, '', ?, '', ?, ?)",
                (task_id, name, meta_payload, now, now),
            )
            conn.commit()
    finally:
        conn.close()
    return task_id


def update_task(task_id: str, **fields: Any) -> None:
    """Update arbitrary fields of a task (status, progress, message, result_json, error)."""
    init_registry()
    allowed = {"status", "progress", "message", "result_json", "error"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    updates["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k}} = ?" for k in updates.keys())
    values = list(updates.values()) + [task_id]
    conn = _conn()
    try:
        with _lock:
            conn.execute(f"UPDATE tasks SET {set_clause}} WHERE id = ?", values)
            conn.commit()
    finally:
        conn.close()


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single task by ID."""
    init_registry()
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["result"] = json.loads(d.get("result_json", "null"))
        except Exception:
            d["result"] = None
        return d
    finally:
        conn.close()


def list_tasks(limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List recent tasks, optionally filtered by status."""
    init_registry()
    conn = _conn()
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def mark_done(task_id: str, result: Any, message: str = "Completed") -> None:
    """Mark a task as completed with its result payload."""
    update_task(
        task_id,
        status="DONE",
        progress=100.0,
        message=message,
        result_json=json.dumps(result, default=str),
    )


def mark_failed(task_id: str, error: str) -> None:
    """Mark a task as failed with an error message."""
    update_task(task_id, status="FAILED", error=str(error)[:2000], message="Failed")


def status_summary() -> Dict[str, int]:
    """Return a status-count breakdown for dashboards."""
    init_registry()
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status"
        ).fetchall()
        return {r["status"]: r["cnt"] for r in rows}
    finally:
        conn.close()

