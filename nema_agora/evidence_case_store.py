"""Append-only persistence and deterministic transition reconstruction for NEMA-AGORA cases."""
from __future__ import annotations

from dataclasses import asdict
import json
import sqlite3
from pathlib import Path
from typing import Any

from .evidence_case import (
    ALLOWED_DECISIONS,
    ALLOWED_STATES,
    AdvisoryFinding,
    EvidenceCase,
    EvidenceReference,
    HumanReview,
    validate_evidence_case,
)


class EvidenceCaseStore:
    """SQLite append-only case store; effective state is reconstructed from immutable events."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS evidence_cases (
                    case_id TEXT PRIMARY KEY,
                    provenance_fingerprint TEXT UNIQUE NOT NULL,
                    state TEXT NOT NULL,
                    case_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    stored_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS evidence_case_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    state TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(case_id) REFERENCES evidence_cases(case_id)
                );
                CREATE INDEX IF NOT EXISTS idx_evidence_case_events_case
                    ON evidence_case_events(case_id, event_id);
                CREATE TRIGGER IF NOT EXISTS evidence_cases_no_update
                BEFORE UPDATE ON evidence_cases
                BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;
                CREATE TRIGGER IF NOT EXISTS evidence_cases_no_delete
                BEFORE DELETE ON evidence_cases
                BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;
                CREATE TRIGGER IF NOT EXISTS evidence_case_events_no_update
                BEFORE UPDATE ON evidence_case_events
                BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;
                CREATE TRIGGER IF NOT EXISTS evidence_case_events_no_delete
                BEFORE DELETE ON evidence_case_events
                BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;
                """
            )

    @staticmethod
    def _case_from_dict(data: dict[str, Any]) -> EvidenceCase:
        evidence = tuple(EvidenceReference(**item) for item in data.get("evidence", ()))
        findings = tuple(
            AdvisoryFinding(
                finding_id=item["finding_id"],
                model_id=item["model_id"],
                model_version=item["model_version"],
                summary=item["summary"],
                confidence=item["confidence"],
                input_fingerprints=tuple(item["input_fingerprints"]),
                generated_at=item["generated_at"],
                advisory_only=item.get("advisory_only", True),
            )
            for item in data.get("findings", ())
        )
        review_data = data.get("review")
        review = HumanReview(**review_data) if review_data else None
        return EvidenceCase(
            case_id=data["case_id"],
            created_at=data["created_at"],
            state=data["state"],
            observation_fingerprint=data["observation_fingerprint"],
            evidence=evidence,
            findings=findings,
            review=review,
            provenance_fingerprint=data["provenance_fingerprint"],
        )

    def append(self, case: EvidenceCase) -> None:
        validation = validate_evidence_case(case)
        if not validation["valid"]:
            raise ValueError(f"invalid evidence case: {validation['issues']}")
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO evidence_cases
                   (case_id, provenance_fingerprint, state, case_json, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    case.case_id,
                    case.provenance_fingerprint,
                    case.state,
                    json.dumps(case.to_dict(), sort_keys=True, ensure_ascii=False),
                    case.created_at,
                ),
            )

    def get(self, case_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT case_id, provenance_fingerprint, state, case_json, created_at, stored_at "
                "FROM evidence_cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        return dict(row) if row else None

    def list(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT case_id, provenance_fingerprint, state, case_json, created_at, stored_at "
                "FROM evidence_cases ORDER BY stored_at, case_id"
            ).fetchall()
        return [dict(row) for row in rows]

    def count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM evidence_cases").fetchone()[0])

    def load_case(self, case_id: str, *, effective: bool = True) -> EvidenceCase:
        row = self.get(case_id)
        if row is None:
            raise KeyError(case_id)
        try:
            case = self._case_from_dict(json.loads(row["case_json"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("stored evidence case is malformed") from exc
        if (
            case.case_id != row["case_id"]
            or case.provenance_fingerprint != row["provenance_fingerprint"]
            or not validate_evidence_case(case)["valid"]
        ):
            raise ValueError("stored evidence case failed integrity validation")
        if not effective:
            return case

        effective_case = case
        for event in self.list_events(case_id):
            try:
                payload = json.loads(event["event_json"])
            except json.JSONDecodeError as exc:
                raise ValueError("stored case event is malformed") from exc
            if payload.get("case_provenance_fingerprint") != case.provenance_fingerprint:
                raise ValueError("case event provenance mismatch")
            if event["event_type"] == "HUMAN_REVIEW":
                if effective_case.state not in {"READY_FOR_REVIEW", "REVIEWED"}:
                    raise ValueError("invalid human-review transition")
                decision = payload.get("decision")
                if decision not in ALLOWED_DECISIONS - {"PENDING"}:
                    raise ValueError("invalid human-review decision in event history")
                effective_case = EvidenceCase(
                    effective_case.case_id,
                    effective_case.created_at,
                    "REVIEWED",
                    effective_case.observation_fingerprint,
                    effective_case.evidence,
                    effective_case.findings,
                    HumanReview(
                        reviewer_id=event["actor_id"],
                        role=event["role"],
                        decision=decision,
                        reviewed_at=event["created_at"],
                        notes=payload.get("notes", ""),
                    ),
                    effective_case.provenance_fingerprint,
                )
            elif event["event_type"] == "EXPORT_AUTHORISED":
                if effective_case.state != "REVIEWED" or effective_case.review is None:
                    raise ValueError("invalid export transition")
                if payload.get("official_submission") is not False or payload.get("execution_gate") != "CLOSED":
                    raise ValueError("unsafe export event")
                effective_case = EvidenceCase(
                    effective_case.case_id,
                    effective_case.created_at,
                    "EXPORTED",
                    effective_case.observation_fingerprint,
                    effective_case.evidence,
                    effective_case.findings,
                    effective_case.review,
                    effective_case.provenance_fingerprint,
                )
            else:
                raise ValueError(f"unsupported case event type: {event['event_type']}")
            if event["state"] != effective_case.state:
                raise ValueError("case event state mismatch")
        return effective_case

    def append_event(
        self,
        *,
        case_id: str,
        event_type: str,
        state: str,
        actor_id: str,
        role: str,
        event: dict[str, Any],
        created_at: str,
    ) -> int:
        if not all(value.strip() for value in (case_id, event_type, state, actor_id, role, created_at)):
            raise ValueError("event identity fields are required")
        if state not in ALLOWED_STATES:
            raise ValueError("invalid event state")
        if not isinstance(event, dict):
            raise ValueError("event must be a mapping")
        with self._connect() as conn:
            exists = conn.execute(
                "SELECT provenance_fingerprint FROM evidence_cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
            if exists is None:
                raise KeyError(case_id)
        if event.get("case_provenance_fingerprint") != exists["provenance_fingerprint"]:
            raise ValueError("event provenance fingerprint is required and must match the case")
        # Reconstruct before appending so a new event can only extend a valid history.
        current = self.load_case(case_id)
        if event_type == "HUMAN_REVIEW":
            if state != "REVIEWED" or current.state not in {"READY_FOR_REVIEW", "REVIEWED"}:
                raise ValueError("invalid human-review transition")
        elif event_type == "EXPORT_AUTHORISED":
            if state != "EXPORTED" or current.state != "REVIEWED":
                raise ValueError("invalid export transition")
            if event.get("official_submission") is not False or event.get("execution_gate") != "CLOSED":
                raise ValueError("unsafe export event")
        else:
            raise ValueError(f"unsupported case event type: {event_type}")
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO evidence_case_events
                   (case_id, event_type, state, actor_id, role, event_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    case_id, event_type, state, actor_id, role,
                    json.dumps(event, sort_keys=True, ensure_ascii=False),
                    created_at,
                ),
            )
            return int(cur.lastrowid)

    def list_events(self, case_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT event_id, case_id, event_type, state, actor_id, role,
                          event_json, created_at
                   FROM evidence_case_events WHERE case_id = ? ORDER BY event_id""",
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]
