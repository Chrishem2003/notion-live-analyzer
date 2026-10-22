from __future__ import annotations

import json
import re
from collections import deque
from pathlib import Path
from threading import RLock
from typing import Any

from .run_models import IntelligenceRun

MAX_RUN_RECORD_BYTES = 262_144
MAX_EVENTS_PER_RUN = 200
MAX_NESTING_DEPTH = 8
_SENSITIVE_KEY_PARTS = (
    "api_key", "apikey", "token", "secret", "password", "authorization",
    "credential", "private_key", "access_key",
)
_SECRET_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]+=*"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,;]+"),
)


def _sanitize(value: Any, *, key: str = "", depth: int = 0) -> Any:
    """Bound and redact untrusted run metadata before it reaches the audit log."""
    normalized_key = key.lower().replace("-", "_")
    if any(part in normalized_key for part in _SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    if depth > MAX_NESTING_DEPTH:
        return "[MAX_DEPTH]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        text = value[:4_000]
        for pattern in _SECRET_PATTERNS:
            text = pattern.sub(lambda match: (match.group(1) if match.lastindex else "") + "[REDACTED]", text)
        return text
    if isinstance(value, dict):
        return {
            str(item_key)[:120]: _sanitize(item_value, key=str(item_key), depth=depth + 1)
            for item_key, item_value in list(value.items())[:100]
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(item, depth=depth + 1) for item in value[:100]]
    # Do not serialize arbitrary object reprs: they can contain credentials.
    return f"[UNSUPPORTED:{type(value).__name__}]"


class RunRecorder:
    """Append JSONL run evidence with bounds and basic secret redaction.

    The log is local filesystem storage, not a durable hosted audit service.
    Redaction is defense-in-depth and does not replace keeping secrets out of
    event metadata at the source.
    """

    def __init__(self, path: str = "data/intelligence_runs.jsonl") -> None:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("A non-empty run log path is required.")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def record(self, run: IntelligenceRun) -> None:
        if not isinstance(run, IntelligenceRun):
            raise TypeError("run must be an IntelligenceRun.")
        if len(run.events) > MAX_EVENTS_PER_RUN:
            raise ValueError(f"A run may contain at most {MAX_EVENTS_PER_RUN} events.")
        payload = _sanitize({
            "id": run.id,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "status": run.status,
            "error": run.error,
            "metadata": run.metadata,
            "events": [
                {
                    "name": event.name,
                    "status": event.status,
                    "timestamp": event.timestamp,
                    "data": event.data,
                }
                for event in run.events
            ],
        })
        try:
            line = json.dumps(
                payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("Run evidence must be JSON-safe and finite.") from exc
        if len(line.encode("utf-8")) > MAX_RUN_RECORD_BYTES:
            raise ValueError("Run evidence exceeds the 262144-byte record limit.")
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()

    def read_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("limit must be an integer between 1 and 1000.")
        if not self.path.exists():
            return []
        recent: deque[tuple[int, str]] = deque(maxlen=limit)
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if line.strip():
                    recent.append((line_number, line))
        records = []
        for line_number, line in recent:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Run log contains invalid JSON at line {line_number}."
                ) from exc
        return records
