"""Phase 159 — reconciliation of Phase 157 monitors and Phase 158 reviews."""
from __future__ import annotations
from typing import Any, Mapping, Sequence
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_continuity_registry_monitor_phase157 import validate_lifecycle_decision_continuity_registry_monitor
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_continuity_registry_review_phase158 import validate_lifecycle_decision_continuity_registry_review

POLICY_VERSION = "phase159-v1"
STATES = ("NO_HISTORY", "RECONCILED", "CONTROL_REQUIRED")

def reconcile_lifecycle_decision_continuity_registry_reviews(
    monitor_reports: Sequence[Mapping[str, Any]], reviews: Sequence[Mapping[str, Any]], *, expected_review_count: int | None = None
) -> dict[str, Any]:
    findings: list[str] = []
    monitors: list[dict[str, Any]] = []
    valid_reviews: list[dict[str, Any]] = []
    for m in monitor_reports:
        try: monitors.append(validate_lifecycle_decision_continuity_registry_monitor(m))
        except (ValueError, KeyError): findings.append("INVALID_MONITOR")
    for r in reviews:
        try: valid_reviews.append(validate_lifecycle_decision_continuity_registry_review(r))
        except (ValueError, KeyError): findings.append("INVALID_REVIEW")
    mf = [m["monitor_fingerprint"] for m in monitors]
    rf = [r["review_fingerprint"] for r in valid_reviews]
    if len(mf) != len(set(mf)): findings.append("DUPLICATE_MONITOR_FINGERPRINT")
    if len(rf) != len(set(rf)): findings.append("DUPLICATE_REVIEW_FINGERPRINT")
    by_monitor: dict[str, list[dict[str, Any]]] = {}
    for r in valid_reviews: by_monitor.setdefault(r["monitor_fingerprint"], []).append(r)
    monitor_ids = set(mf)
    for m in monitors:
        matches = by_monitor.get(m["monitor_fingerprint"], [])
        if not matches: findings.append("UNREVIEWED_MONITOR")
        if len(matches) > 1: findings.append("MULTIPLE_REVIEWS_FOR_MONITOR")
        for r in matches:
            if r["monitor_state"] != m["state"]: findings.append("MONITOR_STATE_MISMATCH")
            if r["monitor_recommendation"] != m["recommendation"]: findings.append("RECOMMENDATION_MISMATCH")
            allowed = {"ACKNOWLEDGED":("CONTINUITY_HEALTHY",),"REVIEW_CONTINUITY":("NO_HISTORY",),"PRESERVE_AND_ESCALATE":("CONTROL_REQUIRED",),"ESCALATED":("NO_HISTORY","CONTROL_REQUIRED")}
            if r["monitor_state"] not in allowed[r["outcome"]]: findings.append("OUTCOME_STATE_MISMATCH")
    for r in valid_reviews:
        if r["monitor_fingerprint"] not in monitor_ids: findings.append("ORPHAN_REVIEW")
    if expected_review_count is not None and len(valid_reviews) != expected_review_count: findings.append("REVIEW_COUNT_MISMATCH")
    state = "NO_HISTORY" if not monitor_reports and not reviews else ("RECONCILED" if not findings else "CONTROL_REQUIRED")
    payload = {
        "policy_version": POLICY_VERSION, "state": state, "monitor_count": len(monitor_reports),
        "valid_monitor_count": len(monitors), "review_count": len(reviews),
        "valid_review_count": len(valid_reviews), "findings": sorted(set(findings)),
        "read_only": True, "human_governed": True, "automatic_repair_performed": False,
        "execution_gate_closed": True, "execution_permitted": False, "execution_performed": False,
        "environmental_conclusion": None, "regulatory_conclusion": None,
        "enforcement_action": None, "emergency_action": None,
        "interpretation": "LIFECYCLE_DECISION_CONTINUITY_REGISTRY_REVIEW_RECONCILIATION",
    }
    return dict(payload, reconciliation_fingerprint=fingerprint(payload))

def validate_lifecycle_decision_continuity_registry_review_reconciliation(result: Mapping[str, Any]) -> dict[str, Any]:
    required = ("policy_version","state","monitor_count","valid_monitor_count","review_count","valid_review_count","findings","read_only","human_governed","automatic_repair_performed","execution_gate_closed","execution_permitted","execution_performed","reconciliation_fingerprint")
    if not isinstance(result, Mapping) or any(k not in result for k in required): raise ValueError("RECONCILIATION_FIELDS_REQUIRED")
    if result["policy_version"] != POLICY_VERSION or result["state"] not in STATES: raise ValueError("INVALID_RECONCILIATION_STATE")
    if result["read_only"] is not True or result["human_governed"] is not True or result["automatic_repair_performed"] is not False: raise ValueError("INVALID_RECONCILIATION_CONTROLS")
    if result["execution_gate_closed"] is not True or result["execution_permitted"] is not False or result["execution_performed"] is not False: raise ValueError("EXECUTION_GATE_VIOLATION")
    payload = dict(result); supplied = payload.pop("reconciliation_fingerprint")
    if fingerprint(payload) != supplied: raise ValueError("RECONCILIATION_FINGERPRINT_MISMATCH")
    return dict(result)
