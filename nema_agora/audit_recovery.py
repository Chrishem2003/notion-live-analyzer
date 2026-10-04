"""Phase 35 — read-only checkpoint verification and backup comparison.

A checkpoint is only independently useful when its exported copy is protected
outside the database being checked. This module never repairs or mutates a ledger.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from nema_agora.audit_ledger import GENESIS_HASH, POLICY_VERSION as LEDGER_POLICY_VERSION

POLICY_VERSION = "phase35-v1"
CHECKPOINT_SCHEMA = "nema-agora-audit-checkpoint-v1"
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _entry_hash(entry: Mapping[str, Any]) -> str:
    body = {key: entry[key] for key in (
        "sequence", "entry_id", "actor_id", "event_type", "occurred_at",
        "payload", "previous_hash", "policy_version",
    )}
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def export_checkpoint(checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    """Wrap a ledger checkpoint in a versioned portable export envelope."""
    required = ("checkpoint_id", "sequence", "entry_hash", "created_at", "actor_id")
    if any(key not in checkpoint for key in required):
        raise ValueError("Checkpoint is missing required fields.")
    sequence = checkpoint["sequence"]
    digest = checkpoint["entry_hash"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise ValueError("Checkpoint sequence must be a non-negative integer.")
    if not isinstance(digest, str) or not _HASH_RE.fullmatch(digest):
        raise ValueError("Checkpoint entry_hash must be a lowercase SHA-256 digest.")
    if sequence == 0 and digest != GENESIS_HASH:
        raise ValueError("An empty-ledger checkpoint must use the genesis hash.")
    for key in ("checkpoint_id", "created_at", "actor_id"):
        if not isinstance(checkpoint[key], str) or not checkpoint[key].strip():
            raise ValueError(f"Checkpoint {key} is required.")
    return {
        "schema": CHECKPOINT_SCHEMA,
        "checkpoint": {
            "checkpoint_id": checkpoint["checkpoint_id"],
            "sequence": sequence,
            "entry_hash": digest,
            "created_at": checkpoint["created_at"],
            "actor_id": checkpoint["actor_id"],
            "policy_version": str(checkpoint.get("policy_version", LEDGER_POLICY_VERSION)),
        },
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "notice": "Store this export separately from the ledger database. The export is not digitally signed.",
    }


def _checkpoint_payload(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if value.get("schema") == CHECKPOINT_SCHEMA:
        checkpoint = value.get("checkpoint")
    else:
        # Direct checkpoint dictionaries are accepted for service-level use.
        checkpoint = value
    if not isinstance(checkpoint, Mapping):
        raise ValueError("Checkpoint envelope has no checkpoint object.")
    required = ("checkpoint_id", "sequence", "entry_hash", "created_at", "actor_id")
    if any(key not in checkpoint for key in required):
        raise ValueError("Checkpoint is missing required fields.")
    sequence = checkpoint["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise ValueError("Checkpoint sequence must be a non-negative integer.")
    digest = checkpoint["entry_hash"]
    if not isinstance(digest, str) or not _HASH_RE.fullmatch(digest):
        raise ValueError("Checkpoint entry_hash must be a lowercase SHA-256 digest.")
    if sequence == 0 and digest != GENESIS_HASH:
        raise ValueError("An empty-ledger checkpoint must use the genesis hash.")
    if any(not isinstance(checkpoint[k], str) or not checkpoint[k].strip()
           for k in ("checkpoint_id", "created_at", "actor_id")):
        raise ValueError("Checkpoint identity fields must be non-empty strings.")
    return checkpoint


def verify_entries_against_checkpoint(
    entries: Iterable[Mapping[str, Any]], checkpoint_value: Mapping[str, Any],
    *, source_label: str = "ledger",
) -> dict[str, Any]:
    """Verify the full supplied chain and bind it to an externally supplied checkpoint."""
    checkpoint = _checkpoint_payload(checkpoint_value)
    ordered = sorted((dict(e) for e in entries), key=lambda e: e.get("sequence", -1))
    errors: list[str] = []
    previous = GENESIS_HASH
    checkpoint_hash_seen = GENESIS_HASH if checkpoint["sequence"] == 0 else None
    verified = 0

    for expected, entry in enumerate(ordered, 1):
        if entry.get("sequence") != expected:
            errors.append("SEQUENCE_GAP")
        if entry.get("previous_hash") != previous:
            errors.append(f"PREVIOUS_HASH_MISMATCH:{entry.get('sequence')}")
        try:
            computed = _entry_hash(entry)
        except (KeyError, TypeError):
            errors.append(f"ENTRY_SCHEMA_INVALID:{entry.get('sequence')}")
            computed = ""
        if computed != entry.get("entry_hash"):
            errors.append(f"ENTRY_HASH_MISMATCH:{entry.get('sequence')}")
        previous = str(entry.get("entry_hash", ""))
        verified += 1
        if entry.get("sequence") == checkpoint["sequence"]:
            checkpoint_hash_seen = entry.get("entry_hash")

    if verified < checkpoint["sequence"]:
        errors.append("CHECKPOINT_AHEAD_OF_LEDGER")
    elif checkpoint_hash_seen != checkpoint["entry_hash"]:
        errors.append("CHECKPOINT_HASH_MISMATCH")

    return {
        "valid": not errors,
        "source_label": source_label,
        "checkpoint_id": checkpoint["checkpoint_id"],
        "checkpoint_sequence": checkpoint["sequence"],
        "checkpoint_hash_matches": checkpoint_hash_seen == checkpoint["entry_hash"],
        "entries_supplied": len(ordered),
        "entries_verified": verified,
        "ledger_head_hash": previous if ordered else GENESIS_HASH,
        "errors": sorted(set(errors)),
        "policy_version": POLICY_VERSION,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "trust_boundary": "Verification only. Trust depends on protecting the supplied checkpoint outside the ledger under test.",
        "decision_notice": "This is an integrity/recovery check, not proof of environmental truth, regulatory status, NEMA authorization, or production approval.",
    }


def verify_ledger_against_checkpoint(ledger: Any, checkpoint_value: Mapping[str, Any],
                                     *, source_label: str = "current-ledger") -> dict[str, Any]:
    """Verify a ledger without writing to it; fails closed on the ledger's own errors."""
    internal = ledger.verify()
    entries = ledger.list_entries(limit=5000) if internal.get("entries", 0) <= 5000 else []
    result = verify_entries_against_checkpoint(entries, checkpoint_value, source_label=source_label)
    if not internal.get("valid", False):
        result["valid"] = False
        result["errors"] = sorted(set(result["errors"] + ["LEDGER_INTERNAL_VERIFICATION_FAILED"] + list(internal.get("errors", []))))
    result["internal_verification"] = {
        "valid": bool(internal.get("valid", False)),
        "entries": internal.get("entries"),
        "errors": list(internal.get("errors", [])),
    }
    return result


def compare_backup_to_checkpoint(backup_entries: Iterable[Mapping[str, Any]],
                                 checkpoint_value: Mapping[str, Any]) -> dict[str, Any]:
    """Compare an already-loaded backup ledger's entries to an exported checkpoint."""
    return verify_entries_against_checkpoint(backup_entries, checkpoint_value, source_label="backup")
