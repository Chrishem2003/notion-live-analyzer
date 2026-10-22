"""Transactional SQLite repository for NEMA-AGORA case records.

This repository provides local transactional persistence and optimistic concurrency.
It does not provide identity verification, multi-tenant isolation, encryption at rest,
backup/restore, or a guarantee that a hosting disk is durable. Do not expose it as a
production write path until the deployment supplies durable storage and authenticated
authorization at the service boundary.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Any

from nema_agora.core import CATEGORIES, SEVERITIES, STATUSES
from nema_agora.workflow import apply_case_transition


class CaseNotFoundError(LookupError):
    """Raised when a requested case does not exist."""


class ConcurrentCaseUpdateError(RuntimeError):
    """Raised when a caller's expected version is stale."""


MAX_CASE_JSON_BYTES = 65_536
_TEXT_LIMITS = {
    "case_id": 80,
    "district_or_site": 120,
    "category": 120,
    "severity": 20,
    "status": 40,
    "description": 1_500,
    "source": 120,
    "reporter_reference": 120,
}


def _json_object(value: Mapping[str, Any]) -> str:
    if not all(isinstance(key, str) and key.strip() for key in value):
        raise ValueError("Case field names must be non-empty strings.")
    for field_name, maximum in _TEXT_LIMITS.items():
        if field_name not in value:
            continue
        field_value = value[field_name]
        if not isinstance(field_value, str):
            raise ValueError(f"{field_name} must be text.")
        if len(field_value) > maximum:
            raise ValueError(f"{field_name} must be {maximum} characters or fewer.")
    try:
        encoded = json.dumps(dict(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("Case data must contain only finite JSON-compatible values.") from exc
    if len(encoded.encode("utf-8")) > MAX_CASE_JSON_BYTES:
        raise ValueError("Case record exceeds the 65536-byte storage limit.")
    return encoded


def _validate_case_record(record: Mapping[str, Any]) -> dict[str, Any]:
    stored_record = dict(record)
    case_id = stored_record.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("A case ID is required.")
    stored_record["case_id"] = case_id.strip()
    if len(stored_record["case_id"]) > _TEXT_LIMITS["case_id"]:
        raise ValueError("case_id must be 80 characters or fewer.")
    if stored_record.get("status") not in STATUSES:
        raise ValueError("A recognised case status is required.")
    for field_name in ("district_or_site", "description"):
        field_value = stored_record.get(field_name)
        if not isinstance(field_value, str) or not field_value.strip():
            raise ValueError(f"{field_name} is required.")
    category = stored_record.get("category")
    if category not in CATEGORIES:
        raise ValueError("A recognised environmental category is required.")
    severity = stored_record.get("severity")
    if severity not in SEVERITIES:
        raise ValueError("A recognised severity is required.")
    observation_date = stored_record.get("observation_date")
    if not isinstance(observation_date, str) or not observation_date.strip():
        raise ValueError("A YYYY-MM-DD observation_date is required.")
    try:
        parsed_date = date.fromisoformat(observation_date.strip())
    except ValueError as exc:
        raise ValueError("observation_date must use YYYY-MM-DD.") from exc
    if parsed_date.isoformat() != observation_date.strip():
        raise ValueError("observation_date must use canonical YYYY-MM-DD.")
    stored_record["observation_date"] = parsed_date.isoformat()
    latitude, longitude = stored_record.get("latitude"), stored_record.get("longitude")
    if (latitude is None) != (longitude is None):
        raise ValueError("Latitude and longitude must be supplied together.")
    if latitude is not None or longitude is not None:
        if isinstance(latitude, bool) or isinstance(longitude, bool):
            raise ValueError("Coordinates must be numeric, not boolean.")
        try:
            lat, lon = float(latitude), float(longitude)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Coordinates must be numeric.") from exc
        import math
        if not math.isfinite(lat) or not math.isfinite(lon):
            raise ValueError("Coordinates must be finite.")
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError("Coordinates are outside valid latitude/longitude ranges.")
        stored_record["latitude"] = lat
        stored_record["longitude"] = lon
    _json_object(stored_record)
    return stored_record


def _aware_timestamp(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("A timezone-aware ISO-8601 timestamp is required.")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Timestamp must be valid ISO-8601.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone offset.")
    return parsed.isoformat()


class NemaCaseRepository:
    """Store cases and append-only audit events in one SQLite transaction.

    Pass a file path for persistence across process restarts only when the hosting
    platform guarantees that path is on durable storage. Use ':memory:' in tests.
    Actor values are audit metadata supplied by the caller, not authenticated identity.
    """

    def __init__(self, database_path: str | Path) -> None:
        path = str(database_path)
        if not path.strip():
            raise ValueError("A database path is required.")
        # SQLite creates the database file but does not create missing parent
        # directories. Keep in-memory and explicit SQLite URI paths untouched.
        if path != ":memory:" and not path.startswith("file:"):
            Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            path, timeout=5.0, isolation_level=None, check_same_thread=False
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS nema_cases (
                case_id TEXT PRIMARY KEY,
                record_json TEXT NOT NULL,
                version INTEGER NOT NULL CHECK (version >= 1),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS nema_case_audit (
                audit_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL REFERENCES nema_cases(case_id),
                event_type TEXT NOT NULL,
                event_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_nema_case_audit_case_created
                ON nema_case_audit(case_id, created_at, audit_id);
            CREATE TRIGGER IF NOT EXISTS nema_case_audit_no_update
            BEFORE UPDATE ON nema_case_audit
            BEGIN
                SELECT RAISE(ABORT, 'NEMA audit events are append-only');
            END;
            CREATE TRIGGER IF NOT EXISTS nema_case_audit_no_delete
            BEFORE DELETE ON nema_case_audit
            BEGIN
                SELECT RAISE(ABORT, 'NEMA audit events are append-only');
            END;
            """
        )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "NemaCaseRepository":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    def create_case(
        self, record: Mapping[str, Any], *, actor: str, created_at: str
    ) -> tuple[dict[str, Any], int]:
        if not isinstance(record, Mapping):
            raise ValueError("Case record must be a mapping.")
        if not isinstance(actor, str) or not actor.strip() or len(actor.strip()) > 120:
            raise ValueError("Actor metadata must be non-empty and at most 120 characters.")
        timestamp = _aware_timestamp(created_at)
        stored_record = _validate_case_record(record)
        case_id = stored_record["case_id"]
        encoded = _json_object(stored_record)
        event = {
            "event_type": "case_created",
            "case_id": case_id,
            "status": stored_record["status"],
            "actor": actor.strip(),
            "created_at": timestamp,
        }
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                self._connection.execute(
                    "INSERT INTO nema_cases(case_id, record_json, version, created_at, updated_at) "
                    "VALUES (?, ?, 1, ?, ?)",
                    (case_id, encoded, timestamp, timestamp),
                )
                self._insert_audit(case_id, "case_created", event, timestamp)
                self._connection.execute("COMMIT")
            except sqlite3.IntegrityError as exc:
                self._connection.execute("ROLLBACK")
                raise ValueError("A case with this ID already exists.") from exc
            except Exception:
                if self._connection.in_transaction:
                    self._connection.execute("ROLLBACK")
                raise
        return stored_record, 1

    def get_case(self, case_id: str) -> tuple[dict[str, Any], int] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT record_json, version FROM nema_cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["record_json"]), int(row["version"])

    def list_cases(self, *, limit: int = 100) -> list[tuple[dict[str, Any], int]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("Limit must be an integer between 1 and 1000.")
        with self._lock:
            rows = self._connection.execute(
                "SELECT record_json, version FROM nema_cases "
                "ORDER BY created_at DESC, case_id ASC LIMIT ?",
                (limit,),
            ).fetchall()
        return [(json.loads(row["record_json"]), int(row["version"])) for row in rows]

    def transition_case(
        self,
        case_id: str,
        *,
        new_status: str,
        actor: str,
        changed_at: str,
        expected_version: int,
        reason: str = "",
    ) -> tuple[dict[str, Any], dict[str, Any] | None, int]:
        if isinstance(expected_version, bool) or not isinstance(expected_version, int) or expected_version < 1:
            raise ValueError("Expected version must be a positive integer.")
        timestamp = _aware_timestamp(changed_at)
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                row = self._connection.execute(
                    "SELECT record_json, version FROM nema_cases WHERE case_id = ?",
                    (case_id,),
                ).fetchone()
                if row is None:
                    raise CaseNotFoundError(f"Case {case_id!r} was not found.")
                current_version = int(row["version"])
                if current_version != expected_version:
                    raise ConcurrentCaseUpdateError(
                        f"Stale case version: expected {expected_version}, current {current_version}."
                    )
                record = json.loads(row["record_json"])
                updated, event = apply_case_transition(
                    record,
                    new_status=new_status,
                    actor=actor,
                    changed_at=timestamp,
                    reason=reason,
                )
                if event is None:
                    self._connection.execute("COMMIT")
                    return updated, None, current_version
                next_version = current_version + 1
                encoded = _json_object(updated)
                cursor = self._connection.execute(
                    "UPDATE nema_cases SET record_json = ?, version = ?, updated_at = ? "
                    "WHERE case_id = ? AND version = ?",
                    (encoded, next_version, timestamp, case_id, current_version),
                )
                if cursor.rowcount != 1:
                    raise ConcurrentCaseUpdateError("Case changed concurrently; reload before retrying.")
                event = {
                    **event,
                    "audit_id": uuid.uuid4().hex,
                    "version_before": current_version,
                    "version_after": next_version,
                }
                self._insert_audit(case_id, "case_status_transition", event, timestamp)
                self._connection.execute("COMMIT")
                return updated, event, next_version
            except Exception:
                if self._connection.in_transaction:
                    self._connection.execute("ROLLBACK")
                raise

    def list_audit_events(self, case_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("Limit must be an integer between 1 and 1000.")
        with self._lock:
            rows = self._connection.execute(
                "SELECT event_json FROM nema_case_audit WHERE case_id = ? "
                "ORDER BY created_at ASC, audit_id ASC LIMIT ?",
                (case_id, limit),
            ).fetchall()
        return [json.loads(row["event_json"]) for row in rows]

    def _insert_audit(
        self, case_id: str, event_type: str, event: Mapping[str, Any], timestamp: str
    ) -> None:
        audit_id = str(event.get("audit_id") or uuid.uuid4().hex)
        payload = {**dict(event), "audit_id": audit_id, "event_type": event_type}
        self._connection.execute(
            "INSERT INTO nema_case_audit(audit_id, case_id, event_type, event_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (audit_id, case_id, event_type, _json_object(payload), timestamp),
        )
