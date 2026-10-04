"""Phase 17 controlled-shadow operations.

Runs an already-admitted advisory model in an isolated shadow lane. The
admission decision, model identity and source case are bound to every run.
This is not production approval, regulatory action, emergency response or
environmental truth.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
import json
import sqlite3
import uuid
from typing import Any

from nema_agora.admission import ADMITTED, AdmissionStore
from nema_agora.shadow import run_shadow


@dataclass(frozen=True)
class ControlledShadowRun:
    run_id: str
    admission_id: str
    case_id: str
    actor_id: str
    provider: str
    model_version: str
    adapter_name: str
    status: str
    latency_ms: float
    output: dict[str, Any] | None
    error: str | None
    occurred_at: str
    human_review_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ControlledShadowStore:
    """Immutable SQLite ledger for governed shadow executions."""

    def __init__(self, database_path: str):
        self.database_path = str(database_path)
        with sqlite3.connect(self.database_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS controlled_shadow_runs (
                run_id TEXT PRIMARY KEY,
                admission_id TEXT NOT NULL,
                case_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                model_version TEXT NOT NULL,
                adapter_name TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('SHADOW_OK','SHADOW_ERROR')),
                latency_ms REAL NOT NULL,
                output_json TEXT,
                error_text TEXT,
                occurred_at TEXT NOT NULL,
                human_review_required INTEGER NOT NULL CHECK (human_review_required = 1)
            )""")
            db.execute("""CREATE INDEX IF NOT EXISTS idx_controlled_shadow_time
                ON controlled_shadow_runs(occurred_at, run_id)""")
            db.execute("""CREATE INDEX IF NOT EXISTS idx_controlled_shadow_admission
                ON controlled_shadow_runs(admission_id, occurred_at, run_id)""")

    def save(self, result: ControlledShadowRun) -> None:
        with sqlite3.connect(self.database_path) as db:
            db.execute(
                """INSERT INTO controlled_shadow_runs
                (run_id, admission_id, case_id, actor_id, provider, model_version,
                 adapter_name, status, latency_ms, output_json, error_text,
                 occurred_at, human_review_required)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (
                    result.run_id, result.admission_id, result.case_id, result.actor_id,
                    result.provider, result.model_version, result.adapter_name,
                    result.status, result.latency_ms,
                    json.dumps(result.output, ensure_ascii=False, sort_keys=True)
                    if result.output is not None else None,
                    result.error, result.occurred_at,
                ),
            )

    def list(self, *, admission_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            if admission_id:
                rows = db.execute(
                    """SELECT * FROM controlled_shadow_runs
                    WHERE admission_id = ? ORDER BY occurred_at DESC, run_id DESC LIMIT ?""",
                    (admission_id, safe_limit),
                ).fetchall()
            else:
                rows = db.execute(
                    """SELECT * FROM controlled_shadow_runs
                    ORDER BY occurred_at DESC, run_id DESC LIMIT ?""",
                    (safe_limit,),
                ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["output"] = json.loads(item.pop("output_json")) if item.get("output_json") else None
            item["human_review_required"] = bool(item["human_review_required"])
            result.append(item)
        return result


def execute_controlled_shadow(
    *,
    database_path: str,
    record: dict[str, Any],
    admission_id: str,
    actor_id: str,
    adapter: Any,
) -> ControlledShadowRun:
    """Execute only an exact, persisted ADMITTED model candidate."""
    admission = next(
        (x for x in AdmissionStore(database_path).list(limit=200)
         if x["admission_id"] == admission_id),
        None,
    )
    if admission is None:
        raise ValueError("Admission record not found.")
    if admission["decision"] != ADMITTED:
        raise PermissionError("Only ADMITTED_FOR_CONTROLLED_SHADOW models may execute.")
    if not actor_id.strip():
        raise ValueError("Authenticated actor is required.")

    candidate = admission["result"]["candidate"]
    provider = str(getattr(adapter, "provider", "")).strip()
    model_version = str(getattr(adapter, "model_version", "")).strip()
    adapter_name = str(getattr(adapter, "adapter_name", getattr(adapter, "name", ""))).strip()
    if (
        provider != candidate["provider"]
        or model_version != candidate["model_version"]
        or adapter_name != candidate["adapter_name"]
    ):
        raise ValueError("Adapter identity does not match the admitted candidate.")

    result = run_shadow(record, adapter)
    return ControlledShadowRun(
        run_id=f"CSR-{uuid.uuid4().hex[:10].upper()}",
        admission_id=admission_id,
        case_id=result.source_case_id,
        actor_id=actor_id.strip(),
        provider=result.provider,
        model_version=result.model_version,
        adapter_name=adapter_name,
        status=result.status,
        latency_ms=result.latency_ms,
        output=result.output,
        error=result.error,
        occurred_at=datetime.now().astimezone().isoformat(timespec="seconds"),
    )
