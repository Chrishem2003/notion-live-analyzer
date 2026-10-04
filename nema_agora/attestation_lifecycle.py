"""Phase 44 — human-governed attestation lifecycle.

This layer derives a current governance lifecycle from immutable Phase 43
attestations plus an append-only decision ledger. Decisions never mutate or
delete historical attestations. Activation, rejection, revocation and
supersession are explicit human actions and are fail-closed on stale evidence,
conflicts, missing second-person review, or expired approvals.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
import sqlite3
from typing import Any, Iterable, Mapping

from nema_agora.governance_attestation import ATTESTED, REJECTED, STALE, CONTROL_REQUIRED

POLICY_VERSION = "phase44-v1"
PENDING_REVIEW = "PENDING_REVIEW"
ACTIVE = "ACTIVE"
REJECTED_STATE = "REJECTED"
REVOKED = "REVOKED"
EXPIRED = "EXPIRED"
SUPERSEDED = "SUPERSEDED"
STALE_STATE = "STALE"
CONTROL_REQUIRED_STATE = "CONTROL_REQUIRED"

APPROVE = "APPROVE"
REJECT = "REJECT"
REVOKE = "REVOKE"
SUPERSEDE = "SUPERSEDE"
_DECISIONS = frozenset({APPROVE, REJECT, REVOKE, SUPERSEDE})
_ROLES = frozenset({"coordinator", "admin"})
_SAFE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

def _safe(value: Any, label: str) -> str:
    value = str(value).strip()
    if not value or not _SAFE.fullmatch(value):
        raise ValueError(f"{label} must be a stable non-identifying ID.")
    return value

def _fp(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")).hexdigest()

def _parse_time(value: str) -> datetime:
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

class AttestationLifecycleRegistry:
    """Append-only lifecycle decision ledger sharing the pilot SQLite database."""

    def __init__(self, database_path: str):
        self.database_path = str(database_path)
        if not self.database_path.strip():
            raise ValueError("Explicit database path required.")
        with sqlite3.connect(self.database_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS governance_attestation_lifecycle (
                decision_id TEXT PRIMARY KEY,
                attestation_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                role TEXT NOT NULL,
                rationale TEXT NOT NULL,
                decided_at TEXT NOT NULL,
                expires_at TEXT,
                superseding_attestation_id TEXT,
                policy_version TEXT NOT NULL
            )""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS governance_attestation_lifecycle_no_update
                BEFORE UPDATE ON governance_attestation_lifecycle BEGIN
                SELECT RAISE(ABORT,'attestation lifecycle ledger is append-only'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS governance_attestation_lifecycle_no_delete
                BEFORE DELETE ON governance_attestation_lifecycle BEGIN
                SELECT RAISE(ABORT,'attestation lifecycle ledger is append-only'); END""")

    def decide(
        self, *, attestation_id: str, decision: str, actor_id: str, role: str,
        rationale: str, decided_at: str | None = None, expires_at: str | None = None,
        superseding_attestation_id: str | None = None,
    ) -> dict[str, Any]:
        attestation_id = _safe(attestation_id, "attestation_id")
        actor_id = _safe(actor_id, "actor_id")
        if role not in _ROLES:
            raise PermissionError("Only coordinator or admin may change attestation lifecycle.")
        if decision not in _DECISIONS:
            raise ValueError("Unsupported lifecycle decision.")
        rationale = str(rationale).strip()
        if len(rationale) < 3 or len(rationale) > 2000:
            raise ValueError("Lifecycle rationale must contain 3-2000 characters.")
        if expires_at is not None:
            _parse_time(expires_at)
            if decision != APPROVE:
                raise ValueError("expires_at is only valid for APPROVE.")
        if superseding_attestation_id is not None:
            superseding_attestation_id = _safe(superseding_attestation_id, "superseding_attestation_id")
            if decision != SUPERSEDE:
                raise ValueError("superseding_attestation_id is only valid for SUPERSEDE.")
            if superseding_attestation_id == attestation_id:
                raise ValueError("An attestation cannot supersede itself.")
        decided_at = decided_at or datetime.now(timezone.utc).isoformat()
        _parse_time(decided_at)
        decision_id = "LIFE-" + _fp({
            "attestation_id": attestation_id, "decision": decision, "actor_id": actor_id,
            "role": role, "rationale": rationale, "decided_at": decided_at,
            "expires_at": expires_at, "superseding_attestation_id": superseding_attestation_id,
        })[:24].upper()
        row = {
            "decision_id": decision_id, "attestation_id": attestation_id, "decision": decision,
            "actor_id": actor_id, "role": role, "rationale": rationale, "decided_at": decided_at,
            "expires_at": expires_at, "superseding_attestation_id": superseding_attestation_id,
            "policy_version": POLICY_VERSION,
        }
        with sqlite3.connect(self.database_path) as db:
            try:
                db.execute("""INSERT INTO governance_attestation_lifecycle
                    VALUES (?,?,?,?,?,?,?,?,?,?)""", tuple(row.values()))
            except sqlite3.IntegrityError as exc:
                raise ValueError("LIFECYCLE_DECISION_CONFLICT: identical decision already exists.") from exc
        return row

    def list(self, limit: int = 500) -> list[dict[str, Any]]:
        safe = max(1, min(int(limit), 5000))
        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            return [dict(r) for r in db.execute(
                "SELECT * FROM governance_attestation_lifecycle ORDER BY decided_at DESC, decision_id DESC LIMIT ?",
                (safe,),
            ).fetchall()]

def _latest_decisions(decisions: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    latest: dict[str, Mapping[str, Any]] = {}
    for row in decisions:
        aid = str(row.get("attestation_id", "")).strip()
        if not aid:
            continue
        current = latest.get(aid)
        if current is None or (str(row.get("decided_at", "")), str(row.get("decision_id", ""))) > (
            str(current.get("decided_at", "")), str(current.get("decision_id", ""))
        ):
            latest[aid] = row
    return latest

def evaluate_lifecycle(
    attestations: Iterable[Mapping[str, Any]],
    decisions: Iterable[Mapping[str, Any]],
    *,
    reconciliation_fingerprint: str,
    evidence_registry_fingerprint: str,
    provenance_fingerprint: str,
    integrity_valid: bool,
    provenance_complete: bool,
    now: str | None = None,
) -> dict[str, Any]:
    now_dt = _parse_time(now or datetime.now(timezone.utc).isoformat())
    att = {str(x.get("attestation_id", "")): dict(x) for x in attestations if x.get("attestation_id")}
    latest = _latest_decisions(decisions)
    items: list[dict[str, Any]] = []
    for aid, row in att.items():
        exact = (
            row.get("reconciliation_fingerprint") == reconciliation_fingerprint
            and row.get("evidence_registry_fingerprint") == evidence_registry_fingerprint
            and row.get("provenance_fingerprint") == provenance_fingerprint
            and row.get("effective_state") == ATTESTED
        )
        decision = latest.get(aid)
        if not integrity_valid or not provenance_complete or not exact:
            state = STALE_STATE if exact is False else CONTROL_REQUIRED_STATE
            if not integrity_valid or not provenance_complete:
                state = CONTROL_REQUIRED_STATE
        elif decision is None:
            state = PENDING_REVIEW
        elif decision.get("decision") == APPROVE:
            expires = decision.get("expires_at")
            state = EXPIRED if expires and now_dt >= _parse_time(expires) else ACTIVE
        elif decision.get("decision") == REJECT:
            state = REJECTED_STATE
        elif decision.get("decision") == REVOKE:
            state = REVOKED
        elif decision.get("decision") == SUPERSEDE:
            state = SUPERSEDED
        else:
            state = CONTROL_REQUIRED_STATE
        items.append({**row, "latest_decision": dict(decision) if decision else None, "lifecycle_state": state})

    active = [x for x in items if x["lifecycle_state"] == ACTIVE]
    conflicts: list[dict[str, Any]] = []
    by_snapshot: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for item in active:
        key = (
            str(item.get("reconciliation_fingerprint")),
            str(item.get("evidence_registry_fingerprint")),
            str(item.get("provenance_fingerprint")),
        )
        by_snapshot.setdefault(key, []).append(item)
    for key, group in by_snapshot.items():
        if len(group) > 1:
            conflicts.append({"code": "MULTIPLE_ACTIVE_ATTESTATIONS", "snapshot": key,
                              "attestation_ids": sorted(x["attestation_id"] for x in group)})
    if conflicts:
        for item in items:
            if item in active:
                item["lifecycle_state"] = CONTROL_REQUIRED_STATE

    return {
        "policy_version": POLICY_VERSION,
        "current_snapshot": {
            "reconciliation_fingerprint": reconciliation_fingerprint,
            "evidence_registry_fingerprint": evidence_registry_fingerprint,
            "provenance_fingerprint": provenance_fingerprint,
        },
        "items": items,
        "decision_count": len(list(decisions)) if not isinstance(decisions, list) else len(decisions),
        "active_count": sum(x["lifecycle_state"] == ACTIVE for x in items),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "overall_state": CONTROL_REQUIRED_STATE if conflicts or not integrity_valid or not provenance_complete else (
            ACTIVE if any(x["lifecycle_state"] == ACTIVE for x in items) else PENDING_REVIEW
        ),
        "evaluated_at": now_dt.isoformat(),
        "notice": "Lifecycle state is explicit human governance evidence. It never authorizes production, NEMA integration, regulatory action, enforcement, emergency response, or autonomous decisions.",
    }
