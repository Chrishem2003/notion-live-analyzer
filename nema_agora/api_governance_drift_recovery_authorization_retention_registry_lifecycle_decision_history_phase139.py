"""Phase 139 — continuity snapshots for authorization-history registry lifecycle decisions."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_phase137 import (
    validate_authorization_history_registry_decision,
)

POLICY_VERSION = "phase139-v1"


def build_authorization_history_registry_decision_continuity(
    decisions: Sequence[Mapping[str, Any]],
    *,
    captured_at: str,
    sequence: int,
    previous_snapshot_fingerprint: str | None = None,
) -> dict[str, Any]:
    if not isinstance(decisions, Sequence) or isinstance(decisions, (str, bytes)):
        raise ValueError("INVALID_DECISIONS")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise ValueError("INVALID_SEQUENCE")
    if not isinstance(captured_at, str) or not captured_at.strip():
        raise ValueError("CAPTURE_TIME_REQUIRED")
    valid = [validate_authorization_history_registry_decision(x) for x in decisions]
    decision_fingerprints = [x["decision_fingerprint"] for x in valid]
    if len(decision_fingerprints) != len(set(decision_fingerprints)):
        raise ValueError("DUPLICATE_DECISION_IDENTITY")

    payload = {
        "policy_version": POLICY_VERSION,
        "captured_at": captured_at,
        "sequence": sequence,
        "previous_snapshot_fingerprint": previous_snapshot_fingerprint,
        "decision_count": len(valid),
        "decisions": valid,
        "human_governed": True,
        "execution_gate_closed": True,
        "execution_permitted": False,
        "execution_performed": False,
        "automatic_repair_performed": False,
        "interpretation": "AUTHORIZATION_HISTORY_REGISTRY_DECISION_CONTINUITY",
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
        "emergency_action": None,
    }
    return dict(payload, snapshot_fingerprint=fingerprint(payload))


def validate_authorization_history_registry_decision_snapshot(
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        raise ValueError("INVALID_SNAPSHOT")
    required = (
        "policy_version", "captured_at", "sequence",
        "previous_snapshot_fingerprint", "decision_count", "decisions",
        "human_governed", "execution_gate_closed", "execution_permitted",
        "execution_performed", "automatic_repair_performed",
        "snapshot_fingerprint",
    )
    for key in required:
        if key not in snapshot:
            raise ValueError("SNAPSHOT_FIELDS_REQUIRED")
    if snapshot["policy_version"] != POLICY_VERSION:
        raise ValueError("SNAPSHOT_POLICY_VIOLATION")
    if snapshot["human_governed"] is not True or snapshot["execution_gate_closed"] is not True:
        raise ValueError("SNAPSHOT_CONTROL_VIOLATION")
    if snapshot["execution_permitted"] is not False or snapshot["execution_performed"] is not False:
        raise ValueError("SNAPSHOT_EXECUTION_VIOLATION")
    if snapshot["automatic_repair_performed"] is not False:
        raise ValueError("SNAPSHOT_REPAIR_VIOLATION")
    if not isinstance(snapshot["decisions"], list) or snapshot["decision_count"] != len(snapshot["decisions"]):
        raise ValueError("SNAPSHOT_COUNT_MISMATCH")
    for decision in snapshot["decisions"]:
        validate_authorization_history_registry_decision(decision)
    payload = dict(snapshot)
    supplied = payload.pop("snapshot_fingerprint")
    if fingerprint(payload) != supplied:
        raise ValueError("SNAPSHOT_FINGERPRINT_MISMATCH")
    return dict(snapshot)


def reconcile_authorization_history_registry_decision_history(
    snapshots: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(snapshots, Sequence) or isinstance(snapshots, (str, bytes)):
        raise ValueError("INVALID_SNAPSHOTS")

    findings: list[dict[str, Any]] = []
    valid: list[dict[str, Any]] = []
    for index, snapshot in enumerate(snapshots):
        try:
            valid.append(validate_authorization_history_registry_decision_snapshot(snapshot))
        except ValueError as exc:
            findings.append({"code": "INVALID_SNAPSHOT", "index": index, "reason": str(exc)})

    for value, count in Counter(x["sequence"] for x in valid).items():
        if count > 1:
            findings.append({"code": "DUPLICATE_SEQUENCE", "sequence": value})
    for value, count in Counter(x["snapshot_fingerprint"] for x in valid).items():
        if count > 1:
            findings.append({"code": "DUPLICATE_SNAPSHOT", "fingerprint": value})

    ordered = sorted(valid, key=lambda x: x["sequence"])
    for index, snapshot in enumerate(ordered):
        if index == 0:
            if snapshot["sequence"] != 1:
                findings.append({"code": "HISTORY_MUST_START_AT_ONE", "sequence": snapshot["sequence"]})
            if snapshot["previous_snapshot_fingerprint"] is not None:
                findings.append({"code": "UNEXPECTED_FIRST_PREDECESSOR", "sequence": snapshot["sequence"]})
        else:
            previous = ordered[index - 1]
            if snapshot["sequence"] != previous["sequence"] + 1:
                findings.append({
                    "code": "SEQUENCE_GAP",
                    "previous": previous["sequence"],
                    "observed": snapshot["sequence"],
                })
            if snapshot["previous_snapshot_fingerprint"] != previous["snapshot_fingerprint"]:
                findings.append({
                    "code": "PREDECESSOR_MISMATCH",
                    "sequence": snapshot["sequence"],
                })

        if any(
            decision["human_authorized"] is not True
            or decision["execution_gate_closed"] is not True
            or decision["execution_permitted"] is not False
            or decision["execution_performed"] is not False
            or decision["automatic_repair_performed"] is not False
            for decision in snapshot["decisions"]
        ):
            findings.append({"code": "EXECUTION_GATE_VIOLATION", "sequence": snapshot["sequence"]})

    findings.sort(key=lambda x: (
        x.get("code", ""),
        str(x.get("index", "")),
        str(x.get("sequence", "")),
    ))
    payload = {
        "policy_version": POLICY_VERSION,
        "state": "CONTROL_REQUIRED" if findings else ("HISTORY_READY" if valid else "NO_HISTORY"),
        "snapshot_count": len(snapshots),
        "valid_snapshot_count": len(valid),
        "findings": findings,
        "read_only": True,
        "human_governed": True,
        "execution_gate_closed": True,
        "execution_permitted": False,
        "execution_performed": False,
        "automatic_repair_performed": False,
        "interpretation": "AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY_RECONCILIATION",
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
        "emergency_action": None,
    }
    return dict(payload, reconciliation_fingerprint=fingerprint(payload))


def validate_authorization_history_registry_decision_history_reconciliation(
    result: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(result, Mapping):
        raise ValueError("INVALID_RECONCILIATION")
    required = (
        "policy_version", "state", "snapshot_count", "valid_snapshot_count",
        "findings", "read_only", "human_governed", "execution_gate_closed",
        "execution_permitted", "execution_performed", "automatic_repair_performed",
        "reconciliation_fingerprint",
    )
    for key in required:
        if key not in result:
            raise ValueError(f"MISSING_{key.upper()}")
    if result["policy_version"] != POLICY_VERSION:
        raise ValueError("INVALID_RECONCILIATION_POLICY")
    if result["state"] not in ("NO_HISTORY", "HISTORY_READY", "CONTROL_REQUIRED"):
        raise ValueError("INVALID_RECONCILIATION_STATE")
    if result["read_only"] is not True or result["human_governed"] is not True:
        raise ValueError("INVALID_GOVERNANCE_CONTROLS")
    if (
        result["execution_gate_closed"] is not True
        or result["execution_permitted"] is not False
        or result["execution_performed"] is not False
    ):
        raise ValueError("EXECUTION_MUST_REMAIN_CLOSED")
    if result["automatic_repair_performed"] is not False:
        raise ValueError("AUTOMATIC_REPAIR_FORBIDDEN")
    if not isinstance(result["findings"], list):
        raise ValueError("INVALID_FINDINGS")
    payload = dict(result)
    supplied = payload.pop("reconciliation_fingerprint")
    if fingerprint(payload) != supplied:
        raise ValueError("RECONCILIATION_FINGERPRINT_MISMATCH")
    return dict(result)
