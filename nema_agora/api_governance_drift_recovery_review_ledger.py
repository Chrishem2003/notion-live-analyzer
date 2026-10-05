"""Phase 110 — human-acknowledged recovery review evidence and append-only ledger."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from .api_audit_binding import fingerprint

POLICY_VERSION = "phase110-v1"
ROLES = ("coordinator", "admin")
OUTCOMES = (
    "ACKNOWLEDGED",
    "BACKUP_REVIEWED",
    "RECOVERY_DEFERRED",
    "ESCALATED",
    "NO_ACTION_APPROVED",
)
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value))


def validate_monitor_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Check Phase 109 report integrity before allowing a human review to bind to it."""
    if not isinstance(report, Mapping):
        raise ValueError("MONITOR_REPORT_REQUIRED")
    claimed = report.get("monitor_fingerprint")
    if not _sha256(claimed):
        raise ValueError("INVALID_MONITOR_FINGERPRINT")
    payload = dict(report)
    payload.pop("monitor_fingerprint", None)
    if fingerprint(payload) != claimed:
        raise ValueError("MONITOR_REPORT_FINGERPRINT_MISMATCH")
    if report.get("policy_version") != "phase109-v1":
        raise ValueError("INVALID_MONITOR_POLICY")
    if report.get("state") not in ("MONITORING_CLEAR", "NO_HISTORY", "CONTROL_REQUIRED"):
        raise ValueError("INVALID_MONITOR_STATE")
    if report.get("read_only") is not True or report.get("automatic_repair_performed") is not False:
        raise ValueError("MONITOR_REPORT_NOT_READ_ONLY")
    return dict(report)


def review_recovery_recommendation(
    monitor_report: Mapping[str, Any],
    *,
    actor_id: str,
    role: str,
    outcome: str,
    reviewed_at: str,
    notes: str = "",
) -> dict[str, Any]:
    """Bind an authorized human acknowledgement to the exact immutable monitor report."""
    report = validate_monitor_report(monitor_report)
    if not isinstance(actor_id, str) or not _ID_RE.fullmatch(actor_id):
        raise ValueError("INVALID_REVIEWER_ID")
    if role not in ROLES:
        raise ValueError("REVIEWER_NOT_AUTHORIZED")
    if outcome not in OUTCOMES:
        raise ValueError("INVALID_REVIEW_OUTCOME")
    if not isinstance(reviewed_at, str) or not reviewed_at.strip():
        raise ValueError("REVIEW_TIME_REQUIRED")
    if not isinstance(notes, str) or len(notes) > 2000:
        raise ValueError("INVALID_REVIEW_NOTES")
    if report["state"] in ("CONTROL_REQUIRED", "NO_HISTORY") and outcome == "NO_ACTION_APPROVED":
        raise ValueError("NO_ACTION_NOT_ALLOWED_WITHOUT_CLEAR_HISTORY")

    payload = {
        "monitor_fingerprint": report["monitor_fingerprint"],
        "monitor_state": report["state"],
        "recovery_recommendation": report["recovery_recommendation"],
        "reviewer_actor_id": actor_id,
        "reviewer_role": role,
        "outcome": outcome,
        "reviewed_at": reviewed_at,
        "notes": notes.strip(),
    }
    audit_fingerprint = fingerprint(payload)
    return dict(
        payload,
        review_audit_id="NEMA-AGORA-RECOVERY-REVIEW-" + audit_fingerprint[:24],
        audit_fingerprint=audit_fingerprint,
        state="REVIEW_RECORDED",
        policy_version=POLICY_VERSION,
        interpretation="HUMAN_ACKNOWLEDGED_RECOVERY_REVIEW",
        automatic_recovery_performed=False,
        environmental_conclusion=None,
        regulatory_conclusion=None,
        enforcement_action=None,
    )


def validate_recovery_review(review: Mapping[str, Any]) -> dict[str, Any]:
    """Validate deterministic identity and fingerprint before persistence."""
    required = (
        "monitor_fingerprint", "monitor_state", "recovery_recommendation",
        "reviewer_actor_id", "reviewer_role", "outcome", "reviewed_at", "notes",
        "review_audit_id", "audit_fingerprint",
    )
    if not isinstance(review, Mapping) or any(key not in review for key in required):
        raise ValueError("RECOVERY_REVIEW_FIELDS_REQUIRED")
    if not _sha256(review["monitor_fingerprint"]) or not _sha256(review["audit_fingerprint"]):
        raise ValueError("INVALID_RECOVERY_REVIEW_FINGERPRINT")
    if review["reviewer_role"] not in ROLES:
        raise ValueError("REVIEWER_NOT_AUTHORIZED")
    if review["outcome"] not in OUTCOMES:
        raise ValueError("INVALID_REVIEW_OUTCOME")
    payload = {
        key: review[key] for key in (
            "monitor_fingerprint", "monitor_state", "recovery_recommendation",
            "reviewer_actor_id", "reviewer_role", "outcome", "reviewed_at", "notes",
        )
    }
    expected = fingerprint(payload)
    if review["audit_fingerprint"] != expected:
        raise ValueError("RECOVERY_REVIEW_FINGERPRINT_MISMATCH")
    if review["review_audit_id"] != "NEMA-AGORA-RECOVERY-REVIEW-" + expected[:24]:
        raise ValueError("RECOVERY_REVIEW_ID_MISMATCH")
    return dict(review)


class RecoveryReviewLedger:
    """SQLite append-only ledger for human review of Phase 109 recovery evidence."""

    def __init__(self, database_path: str | Path):
        if not isinstance(database_path, (str, Path)) or not str(database_path).strip():
            raise ValueError("DATABASE_PATH_REQUIRED")
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recovery_review_ledger (
                    review_audit_id TEXT PRIMARY KEY,
                    monitor_fingerprint TEXT NOT NULL UNIQUE,
                    monitor_state TEXT NOT NULL,
                    recovery_recommendation TEXT NOT NULL,
                    reviewer_actor_id TEXT NOT NULL,
                    reviewer_role TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    reviewed_at TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    audit_fingerprint TEXT NOT NULL UNIQUE,
                    review_json TEXT NOT NULL,
                    policy_version TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS recovery_review_ledger_no_update
                BEFORE UPDATE ON recovery_review_ledger
                BEGIN
                    SELECT RAISE(ABORT, 'recovery review ledger is append-only');
                END
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS recovery_review_ledger_no_delete
                BEFORE DELETE ON recovery_review_ledger
                BEGIN
                    SELECT RAISE(ABORT, 'recovery review ledger is append-only');
                END
                """
            )

    def append(self, review: Mapping[str, Any]) -> dict[str, Any]:
        record = validate_recovery_review(review)
        encoded = json.dumps(dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO recovery_review_ledger (
                        review_audit_id, monitor_fingerprint, monitor_state,
                        recovery_recommendation, reviewer_actor_id, reviewer_role,
                        outcome, reviewed_at, notes, audit_fingerprint, review_json,
                        policy_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["review_audit_id"], record["monitor_fingerprint"],
                        record["monitor_state"], record["recovery_recommendation"],
                        record["reviewer_actor_id"], record["reviewer_role"],
                        record["outcome"], record["reviewed_at"], record["notes"],
                        record["audit_fingerprint"], encoded, POLICY_VERSION,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("RECOVERY_REVIEW_CONFLICT") from exc
        return dict(record, ledger_policy_version=POLICY_VERSION)

    def list(self, limit: int = 500) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
            raise ValueError("INVALID_LIMIT")
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT review_json, policy_version FROM recovery_review_ledger ORDER BY rowid ASC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            item = json.loads(row["review_json"])
            item["ledger_policy_version"] = row["policy_version"]
            result.append(item)
        return result

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM recovery_review_ledger").fetchone()
        return int(row["total"])
