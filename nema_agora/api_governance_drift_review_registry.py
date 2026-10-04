"""Phase 105 — persistent governance drift review audit registry.

Persists the immutable human-review evidence emitted by Phase 104.
The registry is evidence infrastructure only: it does not execute actions,
change governance state, or establish environmental/regulatory truth.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from .api_audit_binding import fingerprint

POLICY_VERSION = "phase105-v1"
OUTCOMES = ("ACKNOWLEDGED", "INVESTIGATE", "NO_DRIFT_CONFIRMED", "ESCALATED")
ROLES = ("coordinator", "admin")
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _stable_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value))


def _payload(audit: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "review_id": audit.get("review_id"),
        "drift_id": audit.get("drift_id"),
        "drift_fingerprint": audit.get("drift_fingerprint"),
        "baseline_snapshot_id": audit.get("baseline_snapshot_id"),
        "current_snapshot_id": audit.get("current_snapshot_id"),
        "reviewer_actor_id": audit.get("reviewer_actor_id"),
        "reviewer_role": audit.get("reviewer_role"),
        "outcome": audit.get("outcome"),
        "reviewed_at": audit.get("reviewed_at"),
    }


def validate_review_audit(audit: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "review_id", "drift_id", "drift_fingerprint",
        "baseline_snapshot_id", "current_snapshot_id",
        "reviewer_actor_id", "reviewer_role", "outcome", "reviewed_at",
        "audit_id", "audit_fingerprint",
    )
    if not all(key in audit for key in required):
        raise ValueError("REVIEW_AUDIT_FIELDS_REQUIRED")
    for key in ("review_id", "drift_id", "baseline_snapshot_id", "current_snapshot_id", "reviewer_actor_id", "audit_id"):
        if not _stable_id(audit[key]):
            raise ValueError("INVALID_REVIEW_AUDIT_ID")
    if not _sha256(audit["drift_fingerprint"]) or not _sha256(audit["audit_fingerprint"]):
        raise ValueError("INVALID_REVIEW_AUDIT_FINGERPRINT")
    if audit["reviewer_role"] not in ROLES:
        raise ValueError("REVIEWER_ROLE_NOT_AUTHORIZED")
    if audit["outcome"] not in OUTCOMES:
        raise ValueError("INVALID_REVIEW_OUTCOME")
    if not isinstance(audit["reviewed_at"], str) or not audit["reviewed_at"].strip():
        raise ValueError("REVIEW_TIME_REQUIRED")
    expected = fingerprint(_payload(audit))
    if audit["audit_fingerprint"] != expected:
        raise ValueError("REVIEW_AUDIT_FINGERPRINT_MISMATCH")
    expected_id = "API-DRIFT-REVIEW-AUDIT-" + expected[:24]
    if audit["audit_id"] != expected_id:
        raise ValueError("REVIEW_AUDIT_ID_MISMATCH")
    return dict(audit)


class GovernanceDriftReviewAuditRegistry:
    """Append-only SQLite registry for Phase 104 review audits."""

    def __init__(self, database_path: str | Path):
        if not str(database_path).strip():
            raise ValueError("DATABASE_PATH_REQUIRED")
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS governance_drift_review_audits (
                    audit_id TEXT PRIMARY KEY,
                    review_id TEXT NOT NULL UNIQUE,
                    drift_id TEXT NOT NULL,
                    drift_fingerprint TEXT NOT NULL,
                    baseline_snapshot_id TEXT NOT NULL,
                    current_snapshot_id TEXT NOT NULL,
                    reviewer_actor_id TEXT NOT NULL,
                    reviewer_role TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    reviewed_at TEXT NOT NULL,
                    audit_fingerprint TEXT NOT NULL UNIQUE,
                    policy_version TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS governance_drift_review_audits_no_update
                BEFORE UPDATE ON governance_drift_review_audits
                BEGIN
                    SELECT RAISE(ABORT, 'governance drift review audit registry is append-only');
                END
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS governance_drift_review_audits_no_delete
                BEFORE DELETE ON governance_drift_review_audits
                BEGIN
                    SELECT RAISE(ABORT, 'governance drift review audit registry is append-only');
                END
                """
            )

    def append(self, audit: Mapping[str, Any]) -> dict[str, Any]:
        record = validate_review_audit(audit)
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO governance_drift_review_audits (
                        audit_id, review_id, drift_id, drift_fingerprint,
                        baseline_snapshot_id, current_snapshot_id,
                        reviewer_actor_id, reviewer_role, outcome, reviewed_at,
                        audit_fingerprint, policy_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["audit_id"], record["review_id"], record["drift_id"],
                        record["drift_fingerprint"], record["baseline_snapshot_id"],
                        record["current_snapshot_id"], record["reviewer_actor_id"],
                        record["reviewer_role"], record["outcome"], record["reviewed_at"],
                        record["audit_fingerprint"], POLICY_VERSION,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("DRIFT_REVIEW_AUDIT_CONFLICT") from exc
        return dict(record, policy_version=POLICY_VERSION)

    def list(self, limit: int = 500) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
            raise ValueError("INVALID_LIMIT")
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT audit_id, review_id, drift_id, drift_fingerprint,
                       baseline_snapshot_id, current_snapshot_id,
                       reviewer_actor_id, reviewer_role, outcome, reviewed_at,
                       audit_fingerprint, policy_version
                FROM governance_drift_review_audits
                ORDER BY rowid ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        keys = (
            "audit_id", "review_id", "drift_id", "drift_fingerprint",
            "baseline_snapshot_id", "current_snapshot_id",
            "reviewer_actor_id", "reviewer_role", "outcome", "reviewed_at",
            "audit_fingerprint", "policy_version",
        )
        return [dict(zip(keys, row)) for row in rows]
