"""Phase 154 — reconciliation of continuity review lifecycles and authorizations."""
from __future__ import annotations
from typing import Any, Mapping, Sequence
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_phase152 import validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_lifecycle_decision_phase153 import validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision

POLICY_VERSION = "phase154-v1"
STATES = ("NO_HISTORY", "RECONCILED", "CONTROL_REQUIRED")

def reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decisions(
    lifecycles: Sequence[Mapping[str, Any]], decisions: Sequence[Mapping[str, Any]], *, expected_decision_count: int | None = None
) -> dict[str, Any]:
    findings: list[str] = []
    valid_lifecycles: list[dict[str, Any]] = []
    valid_decisions: list[dict[str, Any]] = []
    for item in lifecycles:
        try: valid_lifecycles.append(validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle(item))
        except (ValueError, KeyError): findings.append("INVALID_LIFECYCLE")
    for item in decisions:
        try: valid_decisions.append(validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision(item))
        except (ValueError, KeyError): findings.append("INVALID_DECISION")
    lf = [x["lifecycle_fingerprint"] for x in valid_lifecycles]
    df = [x["decision_fingerprint"] for x in valid_decisions]
    if len(lf) != len(set(lf)): findings.append("DUPLICATE_LIFECYCLE_FINGERPRINT")
    if len(df) != len(set(df)): findings.append("DUPLICATE_DECISION_FINGERPRINT")
    by_lifecycle: dict[str, list[dict[str, Any]]] = {}
    for d in valid_decisions: by_lifecycle.setdefault(d["lifecycle_fingerprint"], []).append(d)
    lifecycle_ids = set(lf)
    decision_ids = set(df)
    for l in valid_lifecycles:
        matches = by_lifecycle.get(l["lifecycle_fingerprint"], [])
        if not matches: findings.append("LIFECYCLE_WITHOUT_DECISION")
        if len(matches) > 1: findings.append("MULTIPLE_DECISIONS_FOR_LIFECYCLE")
        for d in matches:
            if d["review_fingerprint"] != l["review_fingerprint"]: findings.append("REVIEW_BINDING_MISMATCH")
            if d["monitor_fingerprint"] != l["monitor_fingerprint"]: findings.append("MONITOR_BINDING_MISMATCH")
            if d["lifecycle_state"] != l["state"] or d["lifecycle_outcome"] != l["outcome"]: findings.append("LIFECYCLE_STATE_OR_OUTCOME_MISMATCH")
            allowed = {"AUTHORIZE_REVIEW": ("DEFERRED",), "AUTHORIZE_PRESERVATION": ("ACKNOWLEDGED", "DEFERRED"), "AUTHORIZE_ESCALATION": ("ESCALATED",)}
            if d["lifecycle_state"] not in allowed[d["decision"]]: findings.append("DECISION_STATE_MISMATCH")
            if d["execution_gate_closed"] is not True or d["execution_permitted"] is not False or d["execution_performed"] is not False: findings.append("EXECUTION_GATE_VIOLATION")
    if decision_ids - lifecycle_ids: findings.append("ORPHAN_DECISION")
    if expected_decision_count is not None and len(valid_decisions) != expected_decision_count: findings.append("DECISION_COUNT_MISMATCH")
    state = "NO_HISTORY" if not lifecycles and not decisions else ("RECONCILED" if not findings else "CONTROL_REQUIRED")
    unique_findings = sorted(set(findings))
    payload = {
        "policy_version": POLICY_VERSION, "state": state,
        "lifecycle_count": len(lifecycles), "valid_lifecycle_count": len(valid_lifecycles),
        "decision_count": len(decisions), "valid_decision_count": len(valid_decisions),
        "findings": unique_findings, "read_only": True, "human_governed": True,
        "automatic_repair_performed": False, "execution_gate_closed": True,
        "execution_permitted": False, "execution_performed": False,
        "environmental_conclusion": None, "regulatory_conclusion": None,
        "enforcement_action": None, "emergency_action": None,
        "interpretation": "CONTINUITY_REVIEW_LIFECYCLE_DECISION_RECONCILIATION",
    }
    return dict(payload, reconciliation_fingerprint=fingerprint(payload))

def validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_lifecycle_decision_reconciliation(result: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(result, Mapping): raise ValueError("INVALID_RECONCILIATION")
    required = ("policy_version","state","lifecycle_count","valid_lifecycle_count","decision_count","valid_decision_count","findings","read_only","human_governed","automatic_repair_performed","execution_gate_closed","execution_permitted","execution_performed","reconciliation_fingerprint")
    if any(k not in result for k in required): raise ValueError("RECONCILIATION_FIELDS_REQUIRED")
    if result["policy_version"] != POLICY_VERSION or result["state"] not in STATES: raise ValueError("INVALID_RECONCILIATION_POLICY_STATE")
    if result["read_only"] is not True or result["human_governed"] is not True or result["automatic_repair_performed"] is not False: raise ValueError("INVALID_RECONCILIATION_CONTROLS")
    if result["execution_gate_closed"] is not True or result["execution_permitted"] is not False or result["execution_performed"] is not False: raise ValueError("EXECUTION_GATE_VIOLATION")
    if not isinstance(result["findings"], list): raise ValueError("INVALID_FINDINGS")
    payload = dict(result); supplied = payload.pop("reconciliation_fingerprint")
    if fingerprint(payload) != supplied: raise ValueError("RECONCILIATION_FINGERPRINT_MISMATCH")
    return dict(result)
