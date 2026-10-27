"""Phase 157 — health monitoring for the Phase 156 continuity registry."""
from __future__ import annotations
from typing import Any, Mapping, Sequence
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_continuity_phase155 import validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity_snapshot

POLICY_VERSION = "phase157-v1"
STATES = ("NO_HISTORY", "CONTINUITY_HEALTHY", "CONTROL_REQUIRED")
RECOMMENDATIONS = ("REVIEW_CONTINUITY", "NO_CONTINUITY_ACTION", "PRESERVE_AND_ESCALATE")

def build_lifecycle_decision_continuity_registry_monitor(
    registry_records: Sequence[Mapping[str, Any]], *, expected_count: int | None = None, observed_at: str
) -> dict[str, Any]:
    from datetime import datetime
    try: datetime.fromisoformat(str(observed_at).replace("Z", "+00:00"))
    except ValueError as exc: raise ValueError("INVALID_OBSERVED_AT") from exc
    findings: list[str] = []
    valid: list[dict[str, Any]] = []
    for record in registry_records:
        try: valid.append(validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_continuity_snapshot(record))
        except (ValueError, KeyError): findings.append("INVALID_REGISTRY_RECORD")
    if expected_count is not None and len(registry_records) != expected_count: findings.append("EXPECTED_COUNT_MISMATCH")
    sequences = [x["sequence"] for x in valid]
    fingerprints = [x["snapshot_fingerprint"] for x in valid]
    if len(sequences) != len(set(sequences)): findings.append("DUPLICATE_SEQUENCE")
    if len(fingerprints) != len(set(fingerprints)): findings.append("DUPLICATE_SNAPSHOT_FINGERPRINT")
    ordered = sorted(valid, key=lambda x: x["sequence"])
    if ordered and ordered[0]["sequence"] != 1: findings.append("HISTORY_MUST_START_AT_ONE")
    if ordered and ordered[0]["previous_snapshot_fingerprint"] is not None: findings.append("UNEXPECTED_FIRST_PREDECESSOR")
    for previous, current in zip(ordered, ordered[1:]):
        if current["sequence"] != previous["sequence"] + 1: findings.append("SEQUENCE_GAP")
        if current["previous_snapshot_fingerprint"] != previous["snapshot_fingerprint"]: findings.append("PREDECESSOR_MISMATCH")
    state = "NO_HISTORY" if not registry_records else ("CONTINUITY_HEALTHY" if not findings else "CONTROL_REQUIRED")
    recommendation = {"NO_HISTORY":"REVIEW_CONTINUITY","CONTINUITY_HEALTHY":"NO_CONTINUITY_ACTION","CONTROL_REQUIRED":"PRESERVE_AND_ESCALATE"}[state]
    payload = {
        "policy_version": POLICY_VERSION, "observed_at": observed_at, "state": state,
        "recommendation": recommendation, "registry_count": len(registry_records),
        "valid_registry_count": len(valid), "findings": sorted(set(findings)),
        "read_only": True, "human_governed": True, "automatic_repair_performed": False,
        "execution_gate_closed": True, "execution_permitted": False, "execution_performed": False,
        "environmental_conclusion": None, "regulatory_conclusion": None,
        "enforcement_action": None, "emergency_action": None,
        "interpretation": "LIFECYCLE_DECISION_CONTINUITY_REGISTRY_HEALTH_MONITOR",
    }
    return dict(payload, monitor_fingerprint=fingerprint(payload))

def monitor_registry(registry: Any, *, observed_at: str, expected_count: int | None = None) -> dict[str, Any]:
    return build_lifecycle_decision_continuity_registry_monitor(registry.list(), expected_count=expected_count, observed_at=observed_at)

def validate_lifecycle_decision_continuity_registry_monitor(report: Mapping[str, Any]) -> dict[str, Any]:
    required = ("policy_version","observed_at","state","recommendation","registry_count","valid_registry_count","findings","read_only","human_governed","automatic_repair_performed","execution_gate_closed","execution_permitted","execution_performed","monitor_fingerprint")
    if not isinstance(report, Mapping) or any(k not in report for k in required): raise ValueError("MONITOR_FIELDS_REQUIRED")
    if report["policy_version"] != POLICY_VERSION or report["state"] not in STATES or report["recommendation"] not in RECOMMENDATIONS: raise ValueError("INVALID_MONITOR_POLICY_STATE")
    if report["read_only"] is not True or report["human_governed"] is not True or report["automatic_repair_performed"] is not False: raise ValueError("INVALID_MONITOR_CONTROLS")
    if report["execution_gate_closed"] is not True or report["execution_permitted"] is not False or report["execution_performed"] is not False: raise ValueError("EXECUTION_GATE_VIOLATION")
    if report["state"] == "NO_HISTORY" and report["recommendation"] != "REVIEW_CONTINUITY": raise ValueError("STATE_RECOMMENDATION_MISMATCH")
    if report["state"] == "CONTINUITY_HEALTHY" and report["recommendation"] != "NO_CONTINUITY_ACTION": raise ValueError("STATE_RECOMMENDATION_MISMATCH")
    if report["state"] == "CONTROL_REQUIRED" and report["recommendation"] != "PRESERVE_AND_ESCALATE": raise ValueError("STATE_RECOMMENDATION_MISMATCH")
    payload = dict(report); supplied = payload.pop("monitor_fingerprint")
    if fingerprint(payload) != supplied: raise ValueError("MONITOR_FINGERPRINT_MISMATCH")
    return dict(report)
