"""Disposable SQLite reference harness; not a production storage adapter."""
import json
import sqlite3
import uuid
from collections.abc import Mapping
from typing import Any

from nema_agora.indicator_measurements import validate_indicator_measurement
from nema_agora.measurement_idempotency import canonical_payload_sha256

_ALLOWED_ROLES = {"submitter", "coordinator", "admin"}


class MeasurementWriteError(ValueError):
    pass


class MeasurementWriteConflict(MeasurementWriteError):
    pass


def initialize_reference_ledger(db: sqlite3.Connection) -> None:
    """Create local-only measurement, idempotency, and append-only audit tables."""
    db.executescript("""
    CREATE TABLE IF NOT EXISTS indicator_measurements (
      measurement_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL,
      payload_sha256 TEXT NOT NULL, actor_id TEXT NOT NULL, actor_role TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS measurement_idempotency (
      idempotency_key TEXT PRIMARY KEY, payload_sha256 TEXT NOT NULL,
      measurement_id TEXT NOT NULL UNIQUE REFERENCES indicator_measurements(measurement_id)
    );
    CREATE TABLE IF NOT EXISTS measurement_audit (
      audit_id TEXT PRIMARY KEY, measurement_id TEXT NOT NULL REFERENCES indicator_measurements(measurement_id),
      actor_id TEXT NOT NULL, actor_role TEXT NOT NULL,
      action TEXT NOT NULL CHECK(action = 'measurement_submitted'),
      idempotency_key TEXT NOT NULL, payload_sha256 TEXT NOT NULL
    );
    CREATE TRIGGER IF NOT EXISTS measurement_audit_no_update BEFORE UPDATE ON measurement_audit
      BEGIN SELECT RAISE(ABORT, 'measurement audit is append-only'); END;
    CREATE TRIGGER IF NOT EXISTS measurement_audit_no_delete BEFORE DELETE ON measurement_audit
      BEGIN SELECT RAISE(ABORT, 'measurement audit is append-only'); END;
    """)


def submit_measurement_reference(
    db: sqlite3.Connection, *, measurement_id: str, payload: Mapping[str, Any],
    idempotency_key: str, actor_id: str, actor_role: str,
    fail_after_measurement_insert: bool = False,
) -> dict[str, Any]:
    """Atomically write a measured record, idempotency mapping, and audit event.

    actor_id/actor_role must be derived from trusted server authentication upstream.
    This function is a local test harness and does not authenticate its caller.
    """
    if not all(isinstance(v, str) and v.strip() for v in (measurement_id, actor_id, idempotency_key)):
        raise MeasurementWriteError("measurement_id, actor_id, and idempotency_key are required.")
    if actor_role not in _ALLOWED_ROLES:
        raise MeasurementWriteError("Actor role is not allowed to submit measurements.")
    if not isinstance(payload, Mapping):
        raise MeasurementWriteError("payload must be an object.")
    try:
        normalized = validate_indicator_measurement(payload)
        if normalized.get("status") != "measured":
            raise MeasurementWriteError("Only measured records can be submitted; verification is separate.")
        encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        digest = canonical_payload_sha256(normalized)
    except (TypeError, ValueError) as exc:
        if isinstance(exc, MeasurementWriteError):
            raise
        raise MeasurementWriteError(str(exc)) from exc

    try:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT payload_sha256, measurement_id FROM measurement_idempotency WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        if old:
            if old[0] != digest:
                raise MeasurementWriteConflict("Idempotency key reused with a different payload.")
            db.commit()
            return {"decision": "replay", "measurement_id": old[1], "payload_sha256": digest, "audit_created": False}
        db.execute("INSERT INTO indicator_measurements VALUES (?, ?, ?, ?, ?)", (measurement_id, encoded, digest, actor_id, actor_role))
        if fail_after_measurement_insert:
            raise RuntimeError("Injected failure after measurement insert.")
        db.execute("INSERT INTO measurement_idempotency VALUES (?, ?, ?)", (idempotency_key, digest, measurement_id))
        db.execute("INSERT INTO measurement_audit VALUES (?, ?, ?, ?, 'measurement_submitted', ?, ?)",
                   (str(uuid.uuid4()), measurement_id, actor_id, actor_role, idempotency_key, digest))
        db.commit()
        return {"decision": "new", "measurement_id": measurement_id, "payload_sha256": digest, "audit_created": True}
    except Exception:
        if db.in_transaction:
            db.rollback()
        raise
