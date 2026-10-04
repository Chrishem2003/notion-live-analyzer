"""Phase 41 — governed closure evaluation for reconciliation exceptions.

Phase 41 derives exception closure state from immutable reconciliation results and
append-only resolution events. It never edits source decisions or audit history.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from nema_agora.governance_reconciliation import reconcile_database

POLICY_VERSION = "phase41-v1"
OPEN = "OPEN"
CLOSED = "CLOSED"
CONTROL_REQUIRED = "CONTROL_REQUIRED"
REVIEW_REQUIRED = "REVIEW_REQUIRED"

CLOSEABLE_OUTCOMES = frozenset({
    "CORRECTED_AT_SOURCE",
    "DUPLICATE_CONFIRMED",
    "FALSE_POSITIVE",
})
NON_CLOSING_OUTCOMES = frozenset({"ACKNOWLEDGED", "ESCALATED"})

_EVIDENCE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_EVIDENCE_HASH = re.compile(r"^[0-9a-f]{64}$")


def _fp(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()
    ).hexdigest()


def _evidence_ok(evidence: Mapping[str, Any] | None) -> bool:
    if not isinstance(evidence, Mapping):
        return False
    evidence_id = str(evidence.get("evidence_id", "")).strip()
    evidence_hash = str(evidence.get("evidence_hash", "")).strip()
    return bool(_EVIDENCE_ID.fullmatch(evidence_id) and _EVIDENCE_HASH.fullmatch(evidence_hash))


def _key(item: Mapping[str, Any]) -> tuple[str | None, str | None, str | None]:
    return (
        item.get("exception_code", item.get("code")),
        item.get("decision_kind"),
        item.get("artifact_id"),
    )


def evaluate_closure(
    reconciliation: Mapping[str, Any],
    resolutions: Iterable[Mapping[str, Any]],
    *,
    evidence_by_key: Mapping[tuple[str | None, str | None, str | None], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate whether reconciliation exceptions are explicitly closeable."""
    if not isinstance(reconciliation, Mapping):
        raise ValueError("Reconciliation result is required.")
    reconciliation_fp = str(reconciliation.get("reconciliation_fingerprint", "")).strip()
    if not reconciliation_fp:
        raise ValueError("Reconciliation fingerprint is required.")

    exceptions = reconciliation.get("exceptions") or []
    evidence_by_key = evidence_by_key or {}
    resolution_map: dict[tuple[str | None, str | None, str | None], list[Mapping[str, Any]]] = {}

    for resolution in resolutions:
        payload = resolution.get("payload") if isinstance(resolution, Mapping) else None
        if isinstance(payload, Mapping):
            payload = payload.get("metadata", payload)
            if isinstance(payload, Mapping) and "metadata" in payload and isinstance(payload.get("metadata"), Mapping):
                payload = payload["metadata"]
        if not isinstance(payload, Mapping):
            continue
        if payload.get("resolution_status") != "RESOLVED":
            continue
        if str(payload.get("reconciliation_fingerprint", "")).strip() != reconciliation_fp:
            continue
        key = (
            payload.get("exception_code"),
            payload.get("decision_kind"),
            payload.get("artifact_id"),
        )
        resolution_map.setdefault(key, []).append(payload)

    results: list[dict[str, Any]] = []
    for exc in exceptions:
        if not isinstance(exc, Mapping):
            continue
        key = _key(exc)
        candidates = resolution_map.get(key, [])
        latest = candidates[-1] if candidates else None
        outcome = str(latest.get("outcome", "")).strip() if latest else None
        evidence = evidence_by_key.get(key)

        if latest is None:
            status, code, detail = OPEN, "NO_RESOLUTION", "No matching resolution event exists for the current reconciliation fingerprint."
        elif outcome in CLOSEABLE_OUTCOMES and _evidence_ok(evidence):
            status, code, detail = CLOSED, "CLOSURE_EVIDENCE_ACCEPTED", "Closeable resolution is supported by a stable evidence reference and SHA-256 hash."
        elif outcome in CLOSEABLE_OUTCOMES:
            status, code, detail = REVIEW_REQUIRED, "MISSING_CLOSURE_EVIDENCE", "A closeable outcome requires evidence_id and a valid SHA-256 evidence_hash."
        elif outcome == "ACKNOWLEDGED":
            status, code, detail = REVIEW_REQUIRED, "ACKNOWLEDGED_NOT_CLOSURE", "Acknowledgement records awareness but does not close the exception."
        elif outcome == "ESCALATED":
            status, code, detail = CONTROL_REQUIRED, "ESCALATED_REMAINS_OPEN", "Escalated exceptions remain under human control."
        else:
            status, code, detail = REVIEW_REQUIRED, "UNSUPPORTED_RESOLUTION_STATE", "The resolution does not satisfy an explicit closure rule."

        results.append({
            "exception_code": key[0],
            "decision_kind": key[1],
            "artifact_id": key[2],
            "severity": exc.get("severity"),
            "status": status,
            "closure_code": code,
            "outcome": outcome,
            "detail": detail,
            "reconciliation_fingerprint": reconciliation_fp,
            "evidence_id": evidence.get("evidence_id") if isinstance(evidence, Mapping) and _evidence_ok(evidence) else None,
            "evidence_hash": evidence.get("evidence_hash") if isinstance(evidence, Mapping) and _evidence_ok(evidence) else None,
        })

    closed = sum(r["status"] == CLOSED for r in results)
    unresolved = len(results) - closed
    overall = CLOSED if results and unresolved == 0 else (OPEN if not results else CONTROL_REQUIRED)
    material = {
        "policy_version": POLICY_VERSION,
        "overall_status": overall,
        "exception_count": len(results),
        "closed_count": closed,
        "unresolved_count": unresolved,
        "results": results,
        "reconciliation_fingerprint": reconciliation_fp,
    }
    closure_fingerprint = _fp(material)
    return {
        **material,
        "closure_id": "CLOSE-" + closure_fingerprint[:16].upper(),
        "closure_fingerprint": closure_fingerprint,
        "notice": "Derived closure status only: no source record, reconciliation result, or historical audit event is modified.",
    }


def reconcile_and_evaluate(database_path: str, *, limit: int = 500) -> dict[str, Any]:
    """Run Phase 39 reconciliation and Phase 41 closure evaluation."""
    reconciliation = reconcile_database(database_path, limit=limit)
    from nema_agora.governance_exception_resolution import GovernanceExceptionResolver

    resolutions = GovernanceExceptionResolver(database_path).list_resolutions(limit=500)
    return evaluate_closure(reconciliation, resolutions)
