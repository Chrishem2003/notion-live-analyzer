"""Versioned, deterministic workflow event contract for the Bio-Research pipeline.

This module validates hand-off metadata only. It does not claim to execute jobs,
call Notion, or provide a durable queue; those require a configured adapter.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "1.0"
ALLOWED_STATUSES = frozenset(
    {"queued", "running", "succeeded", "failed", "blocked", "cancelled"}
)
ALLOWED_STAGES = frozenset(
    {
        "project", "literature", "protocol_safety", "sample_data_intake",
        "analysis", "quality_control", "reproducibility", "problem_solving",
        "publication", "closeout",
    }
)


class WorkflowContractError(ValueError):
    """Raised when a workflow event is incomplete or internally inconsistent."""


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkflowContractError(f"{field} must be a non-empty string")
    return value.strip()


def _validate_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise WorkflowContractError("occurred_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise WorkflowContractError("occurred_at must include a timezone")
    return value


@dataclass(frozen=True)
class WorkflowEvent:
    schema_version: str
    event_id: str
    idempotency_key: str
    workflow_id: str
    run_id: str
    event_type: str
    stage: str
    status: str
    occurred_at: str
    payload_digest: str
    evidence_refs: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "WorkflowEvent":
        if not isinstance(raw, Mapping):
            raise WorkflowContractError("event must be a mapping")
        version = _require_text(raw.get("schema_version"), "schema_version")
        if version != SCHEMA_VERSION:
            raise WorkflowContractError(f"unsupported schema_version: {version}")
        stage = _require_text(raw.get("stage"), "stage")
        if stage not in ALLOWED_STAGES:
            raise WorkflowContractError(f"unsupported stage: {stage}")
        status = _require_text(raw.get("status"), "status")
        if status not in ALLOWED_STATUSES:
            raise WorkflowContractError(f"unsupported status: {status}")
        timestamp = _validate_timestamp(_require_text(raw.get("occurred_at"), "occurred_at"))
        digest = _require_text(raw.get("payload_digest"), "payload_digest").lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise WorkflowContractError("payload_digest must be a SHA-256 hex digest")
        refs = raw.get("evidence_refs", ())
        if isinstance(refs, (str, bytes)) or not isinstance(refs, Sequence):
            raise WorkflowContractError("evidence_refs must be a sequence of non-empty strings")
        clean_refs = tuple(_require_text(ref, "evidence_refs[]") for ref in refs)
        return cls(
            schema_version=version,
            event_id=_require_text(raw.get("event_id"), "event_id"),
            idempotency_key=_require_text(raw.get("idempotency_key"), "idempotency_key"),
            workflow_id=_require_text(raw.get("workflow_id"), "workflow_id"),
            run_id=_require_text(raw.get("run_id"), "run_id"),
            event_type=_require_text(raw.get("event_type"), "event_type"),
            stage=stage,
            status=status,
            occurred_at=timestamp,
            payload_digest=digest,
            evidence_refs=clean_refs,
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["evidence_refs"] = list(self.evidence_refs)
        return result


def canonical_payload_digest(payload: Mapping[str, Any]) -> str:
    """Hash JSON-compatible payload deterministically, independent of key order."""
    if not isinstance(payload, Mapping):
        raise WorkflowContractError("payload must be a mapping")
    try:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise WorkflowContractError("payload must contain finite JSON-compatible values") from exc
    return hashlib.sha256(encoded).hexdigest()


def idempotency_key(workflow_id: str, run_id: str, event_type: str, payload_digest: str) -> str:
    """Stable key for safe deduplication; caller must enforce it in durable storage."""
    parts = [
        _require_text(workflow_id, "workflow_id"),
        _require_text(run_id, "run_id"),
        _require_text(event_type, "event_type"),
        _require_text(payload_digest, "payload_digest").lower(),
    ]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def validate_status_transition(previous: str | None, new: str) -> None:
    """Reject impossible terminal-state rewrites while allowing explicit retries."""
    if new not in ALLOWED_STATUSES:
        raise WorkflowContractError(f"unsupported status: {new}")
    if previous is not None and previous not in ALLOWED_STATUSES:
        raise WorkflowContractError(f"unsupported previous status: {previous}")
    if previous in {"succeeded", "cancelled"} and new != previous:
        raise WorkflowContractError(
            f"terminal status {previous!r} cannot transition to {new!r}; create a new run"
        )
    if previous == "failed" and new == "running":
        # Retry is permitted only as a new run, preserving the failed attempt's history.
        raise WorkflowContractError("retry must use a new run_id to preserve attempt history")
