"""Durable idempotency journal for workflow side effects.

The journal prevents blind replay after an ambiguous outcome. For true exactly-once
business effects, the downstream provider must also honor the supplied stable
idempotency key, or the operator must reconcile the uncertain outcome before retry.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


class EffectJournalError(RuntimeError):
    """Base exception for side-effect journal failures."""


class EffectIdentityConflict(EffectJournalError):
    """A stable effect key was reused for a different request."""


class EffectOutcomeUnknown(EffectJournalError):
    """The effect may already have happened; blind replay is unsafe."""


@dataclass(frozen=True)
class EffectPreparation:
    effect_key: str
    state: str
    newly_prepared: bool
    result: Mapping[str, Any] | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _connect(database: str | Path) -> sqlite3.Connection:
    path = str(database)
    if path != ":memory:":
        Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


class EffectJournal:
    """Append-aware state journal for external actions, stored in SQLite.

    States: pending -> confirmed, or pending -> uncertain. Uncertain/pending
    records are never silently replayed. Reconciliation is an explicit operation.
    """

    def __init__(self, database: str | Path):
        self.database = str(database)
        with closing(_connect(self.database)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_effects (
                    effect_key TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    effect_name TEXT NOT NULL,
                    request_digest TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('pending', 'confirmed', 'uncertain')),
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflow_effects_run ON workflow_effects(workflow_id, run_id)"
            )

    def prepare(
        self, *, effect_key: str, workflow_id: str, run_id: str,
        effect_name: str, request: Mapping[str, Any],
    ) -> EffectPreparation:
        for name, value in (("effect_key", effect_key), ("workflow_id", workflow_id),
                            ("run_id", run_id), ("effect_name", effect_name)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(request, Mapping):
            raise ValueError("request must be a mapping")
        encoded = _canonical(request)
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        now = _now()
        with closing(_connect(self.database)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    "SELECT * FROM workflow_effects WHERE effect_key = ?", (effect_key,)
                ).fetchone()
                if existing is None:
                    connection.execute(
                        """INSERT INTO workflow_effects
                        (effect_key, workflow_id, run_id, effect_name, request_digest,
                         state, result_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, 'pending', NULL, ?, ?)""",
                        (effect_key, workflow_id, run_id, effect_name, digest, now, now),
                    )
                    connection.execute("COMMIT")
                    return EffectPreparation(effect_key, "pending", True)
                identity_matches = (
                    existing["workflow_id"] == workflow_id
                    and existing["run_id"] == run_id
                    and existing["effect_name"] == effect_name
                    and existing["request_digest"] == digest
                )
                if not identity_matches:
                    raise EffectIdentityConflict("effect key already exists for a different request identity")
                result = json.loads(existing["result_json"]) if existing["result_json"] else None
                if existing["state"] == "confirmed":
                    connection.execute("COMMIT")
                    return EffectPreparation(effect_key, "confirmed", False, result)
                connection.execute("COMMIT")
                raise EffectOutcomeUnknown(
                    f"effect {effect_key!r} is {existing['state']}; reconcile with the downstream system before retrying"
                )
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def confirm(self, effect_key: str, result: Mapping[str, Any]) -> None:
        encoded = _canonical(result)
        now = _now()
        with closing(_connect(self.database)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT state, result_json FROM workflow_effects WHERE effect_key = ?", (effect_key,)
                ).fetchone()
                if row is None:
                    raise EffectJournalError("cannot confirm an effect that was not prepared")
                if row["state"] == "confirmed":
                    if row["result_json"] != encoded:
                        raise EffectIdentityConflict("confirmed effect cannot be overwritten with a different result")
                    connection.execute("COMMIT")
                    return
                if row["state"] != "pending":
                    raise EffectOutcomeUnknown("uncertain effect requires reconciliation before confirmation")
                connection.execute(
                    "UPDATE workflow_effects SET state='confirmed', result_json=?, updated_at=? WHERE effect_key=? AND state='pending'",
                    (encoded, now, effect_key),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def mark_uncertain(self, effect_key: str) -> None:
        with closing(_connect(self.database)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT state FROM workflow_effects WHERE effect_key = ?", (effect_key,)
                ).fetchone()
                if row is None:
                    raise EffectJournalError("cannot mark an effect that was not prepared")
                if row["state"] == "confirmed":
                    connection.execute("COMMIT")
                    return
                connection.execute(
                    "UPDATE workflow_effects SET state='uncertain', updated_at=? WHERE effect_key=? AND state IN ('pending', 'uncertain')",
                    (_now(), effect_key),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def reconcile(self, effect_key: str, *, confirmed: bool, result: Mapping[str, Any] | None = None) -> None:
        """Record a verified downstream lookup; never infer success from a timeout."""
        if confirmed:
            if result is None:
                raise ValueError("a verified result mapping is required when confirmed=True")
            encoded = _canonical(result)
            target = "confirmed"
        else:
            encoded = None
            target = "pending"
        with closing(_connect(self.database)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT state FROM workflow_effects WHERE effect_key = ?", (effect_key,)
                ).fetchone()
                if row is None:
                    raise EffectJournalError("cannot reconcile an effect that was not prepared")
                if row["state"] == "confirmed" and target != "confirmed":
                    raise EffectJournalError("confirmed effects cannot be reverted to pending")
                connection.execute(
                    "UPDATE workflow_effects SET state=?, result_json=?, updated_at=? WHERE effect_key=?",
                    (target, encoded, _now(), effect_key),
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def get(self, effect_key: str) -> dict[str, Any] | None:
        with closing(_connect(self.database)) as connection:
            row = connection.execute(
                "SELECT * FROM workflow_effects WHERE effect_key = ?", (effect_key,)
            ).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["result"] = json.loads(item.pop("result_json")) if item.get("result_json") else None
        return item


def execute_idempotent_effect(
    journal: EffectJournal, *, effect_key: str, workflow_id: str, run_id: str,
    effect_name: str, request: Mapping[str, Any],
    perform: Callable[[str], Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Run a side effect once locally and pass the stable key to the provider.

    The provider must deduplicate on effect_key to close the crash-after-effect
    window. If the call raises, the outcome is treated as uncertain, not replayed.
    """
    prepared = journal.prepare(
        effect_key=effect_key, workflow_id=workflow_id, run_id=run_id,
        effect_name=effect_name, request=request,
    )
    if prepared.state == "confirmed":
        return prepared.result or {}
    try:
        result = perform(effect_key)
        if not isinstance(result, Mapping):
            raise TypeError("effect provider must return a mapping")
        # Validate serializability before confirming.
        _canonical(result)
        journal.confirm(effect_key, result)
        return result
    except Exception:
        journal.mark_uncertain(effect_key)
        raise
