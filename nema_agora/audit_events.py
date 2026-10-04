"""Phase 36 — governed, idempotent audit event capture.

Only allowlisted event types and metadata-only payloads are accepted. Do not pass
personal data, credentials, free-text reports, or raw observation contents.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from typing import Any, Mapping

from nema_agora.audit_ledger import AuditLedger, _canonical

POLICY_VERSION = "phase36-v1"
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_ALLOWED_STATUS = frozenset({"COMPLETED", "FAILED", "VALID", "INVALID", "CONTROL_REQUIRED", "APPROVED_FOR_PUBLICATION", "REJECTED", "PENDING_HUMAN_REVIEW"})
_ALLOWED_DECISIONS = frozenset({"APPROVE", "REJECT", "HUMAN_REVIEW_REQUIRED", "DEFER", "ADMITTED_FOR_CONTROLLED_SHADOW", "CONTROL_REQUIRED"})
_ALLOWED_ROLES = frozenset({"submitter", "reviewer", "coordinator", "admin"})
_ALLOWED_MODULES = frozenset({"evaluation", "review", "checkpoint", "publication_control", "model_governance", "audit_recovery", "access_control"})
ALLOWED_EVENT_TYPES = frozenset({
    "EVALUATION_COMPLETED",
    "REVIEW_DECISION_RECORDED",
    "CHECKPOINT_CREATED",
    "PUBLICATION_GATE_DECIDED",
    "MODEL_LIFECYCLE_DECIDED",
    "BACKUP_VERIFICATION_COMPLETED",
    "ACCESS_POLICY_DENIED",
})
ALLOWED_PAYLOAD_KEYS = frozenset({
    "artifact_id", "artifact_hash", "decision", "status", "reason_code",
    "policy_version", "counts", "checkpoint_id", "checkpoint_sequence",
    "verification_status", "source_module", "recorded_by_role",
})
FORBIDDEN_KEY_PARTS = (
    "password", "secret", "token", "credential", "email", "phone",
    "address", "name", "birth", "location", "latitude", "longitude",
    "observation_text", "description", "free_text", "transcript",
    "voice", "image", "photo", "personal", "raw_record",
)


def _validate_metadata(value: Any, path: str = "payload") -> Any:
    if isinstance(value, dict):
        clean = {}
        count_keys = {"accepted", "rejected", "total", "warnings", "errors"}
        for key, item in value.items():
            allowed = key in count_keys if path.endswith(".counts") else key in ALLOWED_PAYLOAD_KEYS
            if not isinstance(key, str) or not allowed:
                raise ValueError(f"Unsupported audit metadata key at {path}.")
            lowered = key.lower()
            if any(part in lowered for part in FORBIDDEN_KEY_PARTS):
                raise ValueError(f"Sensitive metadata key rejected at {path}.{key}.")
            if path.endswith(".counts") and (not isinstance(item, int) or isinstance(item, bool) or item < 0):
                raise ValueError(f"Counts must be non-negative integers at {path}.{key}.")
            clean[key] = _validate_metadata(item, f"{path}.{key}")
        return clean
    if isinstance(value, list):
        if len(value) > 50:
            raise ValueError(f"Audit metadata list too large at {path}.")
        return [_validate_metadata(item, path) for item in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if len(value) > 256:
            raise ValueError(f"Audit metadata value too long at {path}.")
        if any(ord(ch) < 32 and ch not in "\t\n\r" for ch in value):
            raise ValueError(f"Control characters rejected at {path}.")
        return value
    raise ValueError(f"Unsupported audit metadata type at {path}.")


class AuditEventCapture:
    """Record approved, metadata-only events in the hash-chained ledger."""

    def __init__(self, ledger: AuditLedger):
        self.ledger = ledger

    def record(self, *, event_id: str, event_type: str, actor_id: str,
               payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(event_id, str) or not _SAFE_ID.fullmatch(event_id.strip()):
            raise ValueError("A stable, non-identifying event_id is required.")
        if event_type not in ALLOWED_EVENT_TYPES:
            raise ValueError("Audit event type is not allowlisted.")
        if not isinstance(actor_id, str) or not actor_id.strip() or len(actor_id) > 128:
            raise ValueError("Authenticated actor ID is required.")
        if not isinstance(payload, Mapping):
            raise ValueError("Audit payload must be an object.")
        clean = _validate_metadata(dict(payload))
        key_material = {"event_id": event_id.strip(), "event_type": event_type}
        entry_id = "EVT-" + hashlib.sha256(_canonical(key_material).encode("utf-8")).hexdigest()[:48].upper()
        body = {
            "event_id": event_id.strip(),
            "event_type": event_type,
            "metadata": clean,
            "capture_policy": POLICY_VERSION,
        }
        try:
            entry = self.ledger.append(
                entry_id=entry_id, actor_id=actor_id.strip(),
                event_type="GOVERNED_AUDIT_EVENT", payload=body,
            )
            return {"recorded": True, "duplicate": False, "entry": entry, "policy_version": POLICY_VERSION}
        except sqlite3.IntegrityError:
            # Idempotency key maps to the deterministic entry ID. Only report a
            # duplicate if the stored event has the same event identity and body.
            with self.ledger._connect() as db:
                row = db.execute(
                    "SELECT payload_json, actor_id FROM audit_ledger WHERE entry_id = ?",
                    (entry_id,),
                ).fetchone()
            if row is None:
                raise
            stored = json.loads(row["payload_json"])
            if stored != body or row["actor_id"] != actor_id.strip():
                raise ValueError("EVENT_ID_CONFLICT: event ID was previously used with different content or actor.")
            return {"recorded": False, "duplicate": True, "entry_id": entry_id,
                    "policy_version": POLICY_VERSION}
