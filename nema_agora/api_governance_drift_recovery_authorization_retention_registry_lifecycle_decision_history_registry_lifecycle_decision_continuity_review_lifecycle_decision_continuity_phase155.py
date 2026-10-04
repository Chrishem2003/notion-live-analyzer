"""Phase 155 — continuity of Phase 153 lifecycle authorization decisions."""
from __future__ import annotations
from typing import Any, Mapping, Sequence
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_phase153 import validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision

POLICY_VERSION = "phase155-v1"
STATES = ("NO_HISTORY", "HISTORY_READY", "CONTROL_REQUIRED")

def build_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity(
    decisions: Sequence[Mapping[str, Any]], *, captured_at: str, sequence: int,
    previous_snapshot_fingerprint: str | None = None
) -> dict[str, Any]:
    from datetime import datetime
    try: datetime.fromisoformat(str(captured_at).replace("Z", "+00:00"))
    except ValueError as exc: raise ValueError("INVALID_CAPTURED_AT") from exc
    if sequence < 1: raise ValueError("INVALID_SEQUENCE")
    if sequence == 1 and previous_snapshot_fingerprint is not None: raise ValueError("UNEXPECTED_PREVIOUS_SNAPSHOT")
    if sequence > 1 and not previous_snapshot_fingerprint: raise ValueError("PREVIOUS_SNAPSHOT_REQUIRED")
    valid = [validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision(d) for d in decisions]
    ids = [d["decision_fingerprint"] for d in valid]
    if len(ids) != len(set(ids)): raise ValueError("DUPLICATE_DECISION_FINGERPRINT")
    payload = {
        "policy_version": POLICY_VERSION, "captured_at": captured_at, "sequence": sequence,
        "previous_snapshot_fingerprint": previous_snapshot_fingerprint,
        "decision_count": len(valid), "decisions": valid,
        "human_governed": True, "automatic_repair_performed": False,
        "execution_gate_closed": True, "execution_permitted": False, "execution_performed": False,
        "environmental_conclusion": None, "regulatory_conclusion": None,
        "enforcement_action": None, "emergency_action": None,
        "interpretation": "LIFECYCLE_DECISION_CONTINUITY_EVIDENCE_ONLY",
    }
    return dict(payload, snapshot_fingerprint=fingerprint(payload))

def validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    required = ("policy_version","captured_at","sequence","previous_snapshot_fingerprint","decision_count","decisions","human_governed","automatic_repair_performed","execution_gate_closed","execution_permitted","execution_performed","snapshot_fingerprint")
    if not isinstance(snapshot, Mapping) or any(k not in snapshot for k in required): raise ValueError("SNAPSHOT_FIELDS_REQUIRED")
    if snapshot["policy_version"] != POLICY_VERSION or not isinstance(snapshot["sequence"], int) or snapshot["sequence"] < 1: raise ValueError("INVALID_SNAPSHOT_POLICY_SEQUENCE")
    if snapshot["human_governed"] is not True or snapshot["automatic_repair_performed"] is not False: raise ValueError("INVALID_SNAPSHOT_CONTROLS")
    if snapshot["execution_gate_closed"] is not True or snapshot["execution_permitted"] is not False or snapshot["execution_performed"] is not False: raise ValueError("EXECUTION_GATE_VIOLATION")
    for d in snapshot["decisions"]: validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision(d)
    if snapshot["decision_count"] != len(snapshot["decisions"]): raise ValueError("DECISION_COUNT_MISMATCH")
    payload = dict(snapshot); supplied = payload.pop("snapshot_fingerprint")
    if fingerprint(payload) != supplied: raise ValueError("SNAPSHOT_FINGERPRINT_MISMATCH")
    return dict(snapshot)

def reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity(snapshots: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    findings: list[str] = []
    valid = []
    for s in snapshots:
        try: valid.append(validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_snapshot(s))
        except (ValueError, KeyError): findings.append("INVALID_SNAPSHOT")
    sequences = [s["sequence"] for s in valid]
    fps = [s["snapshot_fingerprint"] for s in valid]
    if len(sequences) != len(set(sequences)): findings.append("DUPLICATE_SEQUENCE")
    if len(fps) != len(set(fps)): findings.append("DUPLICATE_SNAPSHOT_FINGERPRINT")
    ordered = sorted(valid, key=lambda x: x["sequence"])
    if ordered and ordered[0]["sequence"] != 1: findings.append("HISTORY_MUST_START_AT_ONE")
    for prev, cur in zip(ordered, ordered[1:]):
        if cur["sequence"] != prev["sequence"] + 1: findings.append("SEQUENCE_GAP")
        if cur["previous_snapshot_fingerprint"] != prev["snapshot_fingerprint"]: findings.append("PREDECESSOR_MISMATCH")
    if ordered and ordered[0]["previous_snapshot_fingerprint"] is not None: findings.append("UNEXPECTED_FIRST_PREDECESSOR")
    state = "NO_HISTORY" if not snapshots else ("HISTORY_READY" if not findings else "CONTROL_REQUIRED")
    payload = {
        "policy_version": POLICY_VERSION, "state": state, "snapshot_count": len(snapshots),
        "valid_snapshot_count": len(valid), "findings": sorted(set(findings)),
        "read_only": True, "human_governed": True, "automatic_repair_performed": False,
        "execution_gate_closed": True, "execution_permitted": False, "execution_performed": False,
        "environmental_conclusion": None, "regulatory_conclusion": None,
        "enforcement_action": None, "emergency_action": None,
        "interpretation": "LIFECYCLE_DECISION_CONTINUITY_EVIDENCE_ONLY",
    }
    return dict(payload, reconciliation_fingerprint=fingerprint(payload))

def validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity(result: Mapping[str, Any]) -> dict[str, Any]:
    required = ("policy_version","state","snapshot_count","valid_snapshot_count","findings","read_only","human_governed","automatic_repair_performed","execution_gate_closed","execution_permitted","execution_performed","reconciliation_fingerprint")
    if not isinstance(result, Mapping) or any(k not in result for k in required): raise ValueError("CONTINUITY_FIELDS_REQUIRED")
    if result["policy_version"] != POLICY_VERSION or result["state"] not in STATES: raise ValueError("INVALID_CONTINUITY_STATE")
    if result["read_only"] is not True or result["human_governed"] is not True or result["automatic_repair_performed"] is not False: raise ValueError("INVALID_CONTINUITY_CONTROLS")
    if result["execution_gate_closed"] is not True or result["execution_permitted"] is not False or result["execution_performed"] is not False: raise ValueError("EXECUTION_GATE_VIOLATION")
    payload = dict(result); supplied = payload.pop("reconciliation_fingerprint")
    if fingerprint(payload) != supplied: raise ValueError("CONTINUITY_FINGERPRINT_MISMATCH")
    return dict(result)
