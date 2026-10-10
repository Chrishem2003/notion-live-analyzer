"""Phase 13 AI Evaluation Laboratory for NEMA-AGORA.

This is a reproducible evaluation harness, not a model approval system. It
compares advisory adapters against human-labelled cases without changing live
observations or workflow state.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
import json
import time
import uuid
from typing import Any, Protocol

from nema_agora.evaluation import SUPPORTED_CATEGORIES, validate_advisory_output


class EvaluationAdapter(Protocol):
    provider: str
    model_version: str

    def analyse(self, record: dict[str, Any]) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class LabCase:
    case_id: str
    record: dict[str, Any]
    expected_category: str
    expected_duplicate: bool
    expected_summary_faithful: bool | None = None
    slice_name: str = "all"

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id is required")
        if self.expected_category not in SUPPORTED_CATEGORIES:
            raise ValueError("Unsupported expected category")
        if self.record.get("case_id") != self.case_id:
            raise ValueError("record.case_id must match case_id")
        if not isinstance(self.expected_duplicate, bool):
            raise ValueError("expected_duplicate must be boolean")


@dataclass(frozen=True)
class AdapterMetrics:
    provider: str
    model_version: str
    cases: int
    successful: int
    failures: int
    error_rate: float
    category_accuracy: float
    duplicate_precision: float
    duplicate_recall: float
    duplicate_f1: float
    summary_label_coverage: float
    mean_latency_ms: float
    confidence_brier: float | None
    confidence_cases: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LabResult:
    run_id: str
    created_at: str
    dataset_version: str
    cases: int
    adapters: tuple[AdapterMetrics, ...]
    case_results: tuple[dict[str, Any], ...]
    slice_results: tuple[dict[str, Any], ...]
    readiness: str
    safety_notice: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["adapters"] = [a.to_dict() for a in self.adapters]
        return data


def _ratio(n: int, d: int) -> float:
    return n / d if d else 0.0


def _prediction_category(output: dict[str, Any]) -> str | None:
    value = output.get("predicted_category")
    if isinstance(value, str) and value in SUPPORTED_CATEGORIES:
        return value
    suggestions = output.get("category_suggestions") or []
    if suggestions and isinstance(suggestions[0], dict):
        candidate = suggestions[0].get("category")
        if isinstance(candidate, str) and candidate in SUPPORTED_CATEGORIES:
            return candidate
    return None


def _prediction_duplicate(output: dict[str, Any]) -> bool:
    candidates = output.get("duplicate_candidates") or []
    return isinstance(candidates, list) and bool(candidates)


def _confidence(output: dict[str, Any]) -> float | None:
    value = output.get("confidence")
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if 0.0 <= value <= 1.0 else None


def _adapter_metrics(provider: str, model_version: str, rows: list[dict[str, Any]]) -> AdapterMetrics:
    successful = [r for r in rows if r["status"] == "OK"]
    failures = len(rows) - len(successful)
    category_rows = [r for r in successful if r["predicted_category"] is not None]
    duplicate_rows = [r for r in successful if r["predicted_duplicate"] is not None]
    tp = sum(r["predicted_duplicate"] and r["expected_duplicate"] for r in duplicate_rows)
    fp = sum(r["predicted_duplicate"] and not r["expected_duplicate"] for r in duplicate_rows)
    fn = sum((not r["predicted_duplicate"]) and r["expected_duplicate"] for r in duplicate_rows)
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    f1 = _ratio(2 * precision * recall, precision + recall)
    faithful = [r["summary_faithful"] for r in successful if r["summary_faithful"] is not None]
    confidence_rows = [r for r in successful if r["confidence"] is not None and r["predicted_category"] is not None]
    brier = None
    if confidence_rows:
        brier = sum(
            (r["confidence"] - (1.0 if r["predicted_category"] == r["expected_category"] else 0.0)) ** 2
            for r in confidence_rows
        ) / len(confidence_rows)
    return AdapterMetrics(
        provider=provider,
        model_version=model_version,
        cases=len(rows),
        successful=len(successful),
        failures=failures,
        error_rate=_ratio(failures, len(rows)),
        category_accuracy=_ratio(
            sum(r["predicted_category"] == r["expected_category"] for r in category_rows),
            len(category_rows),
        ),
        duplicate_precision=precision,
        duplicate_recall=recall,
        duplicate_f1=f1,
        summary_label_coverage=_ratio(len(faithful), len(successful)),
        mean_latency_ms=_ratio(sum(r["latency_ms"] for r in rows), len(rows)),
        confidence_brier=brier,
        confidence_cases=len(confidence_rows),
    )


def run_evaluation(
    cases: list[LabCase],
    adapters: dict[str, EvaluationAdapter],
    *,
    dataset_version: str,
) -> LabResult:
    if not cases:
        raise ValueError("At least one labelled evaluation case is required.")
    if not adapters:
        raise ValueError("At least one evaluation adapter is required.")
    if not dataset_version.strip():
        raise ValueError("dataset_version is required.")

    case_results: list[dict[str, Any]] = []
    slice_rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    adapter_metrics: list[AdapterMetrics] = []

    for adapter_name, adapter in adapters.items():
        provider = str(getattr(adapter, "provider", adapter_name)).strip()[:80]
        version = str(getattr(adapter, "model_version", "unknown")).strip()[:120]
        rows: list[dict[str, Any]] = []
        for case in cases:
            started = time.perf_counter()
            status = "OK"
            output: dict[str, Any] | None = None
            error = ""
            try:
                output = adapter.analyse(dict(case.record))
                if not isinstance(output, dict):
                    raise ValueError("Adapter output must be an object.")
                errors = validate_advisory_output(output)
                if errors:
                    raise ValueError("; ".join(errors))
                if output.get("source_case_id") != case.case_id:
                    raise ValueError("source_case_id must match evaluation case.")
            except Exception as exc:
                status = "ERROR"
                error = str(exc)[:500]
            latency_ms = (time.perf_counter() - started) * 1000.0
            predicted_category = _prediction_category(output or {}) if output else None
            predicted_duplicate = _prediction_duplicate(output or {}) if output else None
            confidence = _confidence(output or {}) if output else None
            row = {
                "adapter": adapter_name,
                "provider": provider,
                "model_version": version,
                "case_id": case.case_id,
                "slice": case.slice_name,
                "status": status,
                "error": error,
                "latency_ms": latency_ms,
                "expected_category": case.expected_category,
                "predicted_category": predicted_category,
                "expected_duplicate": case.expected_duplicate,
                "predicted_duplicate": predicted_duplicate,
                "summary_faithful": case.expected_summary_faithful,
                "confidence": confidence,
            }
            rows.append(row)
            case_results.append(row)
            slice_rows.setdefault((adapter_name, case.slice_name), []).append(row)
        adapter_metrics.append(_adapter_metrics(provider, version, rows))

    slice_results = []
    for (adapter_name, slice_name), rows in sorted(slice_rows.items()):
        metric = _adapter_metrics(rows[0]["provider"], rows[0]["model_version"], rows)
        slice_results.append({"adapter": adapter_name, "slice": slice_name, **metric.to_dict()})

    readiness = "NOT_READY"
    if len(cases) >= 25 and all(
        m.error_rate == 0.0 and m.category_accuracy >= 0.80 and m.duplicate_f1 >= 0.80
        for m in adapter_metrics
    ):
        readiness = "READY_FOR_REVIEW"

    return LabResult(
        run_id=f"LAB-{uuid.uuid4().hex[:10].upper()}",
        created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        dataset_version=dataset_version.strip()[:80],
        cases=len(cases),
        adapters=tuple(adapter_metrics),
        case_results=tuple(case_results),
        slice_results=tuple(slice_results),
        readiness=readiness,
        safety_notice=(
            "Evaluation results are measurement evidence only. They do not establish "
            "environmental truth, regulatory status, enforcement priority, or permission "
            "to deploy an AI model. Human review remains mandatory."
        ),
    )


def serialise_lab_result(result: LabResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class EvaluationRunStore:
    """Persist immutable evaluation-run summaries separately from live case facts."""

    def __init__(self, database_path: str):
        import sqlite3
        self.database_path = str(database_path)
        with sqlite3.connect(self.database_path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS evaluation_runs (
                    run_id TEXT PRIMARY KEY,
                    actor_id TEXT NOT NULL,
                    dataset_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    result_json TEXT NOT NULL
                )"""
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_evaluation_runs_time ON evaluation_runs(created_at, run_id)"
            )

    def save(self, result: LabResult, *, actor_id: str) -> None:
        import sqlite3
        if not actor_id.strip():
            raise ValueError("Authenticated actor is required.")
        with sqlite3.connect(self.database_path) as db:
            db.execute(
                "INSERT INTO evaluation_runs (run_id, actor_id, dataset_version, created_at, result_json) VALUES (?, ?, ?, ?, ?)",
                (result.run_id, actor_id, result.dataset_version, result.created_at, serialise_lab_result(result)),
            )

    def list(self, *, limit: int = 25) -> list[dict[str, Any]]:
        import sqlite3
        safe_limit = max(1, min(int(limit), 100))
        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT run_id, actor_id, dataset_version, created_at, result_json "
                "FROM evaluation_runs ORDER BY created_at DESC, run_id DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        return [
            {**dict(row), "result": json.loads(row["result_json"])}
            for row in rows
        ]
