"""Phase 122 — reconciliation of retention authorization decisions against lifecycle evidence."""
from __future__ import annotations

from typing import Any, Mapping
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_lifecycle import validate_retention_lifecycle
from .api_governance_drift_recovery_authorization_retention_decision import validate_retention_decision

POLICY_VERSION = "phase122-v1"
LIFECYCLE_POLICY_VERSION = "phase120-v1"
DECISION_POLICY_VERSION = "phase121-v1"

def _findings(lifecycles: list[Mapping[str, Any]], decisions: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    valid_l, valid_d = [], []
    for item in lifecycles:
        try: valid_l.append(validate_retention_lifecycle(item))
        except ValueError as exc: findings.append({"code": "INVALID_LIFECYCLE", "error": str(exc)})
    for item in decisions:
        try: valid_d.append(validate_retention_decision(item))
        except ValueError as exc: findings.append({"code": "INVALID_DECISION", "error": str(exc)})

    def duplicates(items, key, code):
        seen=set()
        for item in items:
            value=item.get(key)
            if value in seen: findings.append({"code":code,"value":value})
            seen.add(value)

    duplicates(valid_l,"lifecycle_fingerprint","DUPLICATE_LIFECYCLE_FINGERPRINT")
    duplicates(valid_d,"decision_fingerprint","DUPLICATE_DECISION_FINGERPRINT")
    life_by_fp={x["lifecycle_fingerprint"]:x for x in valid_l}
    monitor_fps={x["monitor_fingerprint"] for x in valid_l}
    review_fps={x["review_fingerprint"] for x in valid_l}
    decisions_by_lifecycle={}
    for d in valid_d:
        decisions_by_lifecycle.setdefault(d["lifecycle_fingerprint"], []).append(d)
        life=life_by_fp.get(d["lifecycle_fingerprint"])
        if life is None:
            findings.append({"code":"ORPHAN_DECISION","lifecycle_fingerprint":d["lifecycle_fingerprint"]})
            continue
        if d["monitor_fingerprint"] != life["monitor_fingerprint"]:
            findings.append({"code":"MONITOR_BINDING_MISMATCH","lifecycle_fingerprint":d["lifecycle_fingerprint"]})
        if d["review_fingerprint"] != life["review_fingerprint"]:
            findings.append({"code":"REVIEW_BINDING_MISMATCH","lifecycle_fingerprint":d["lifecycle_fingerprint"]})
        if d["lifecycle_state"] != life["lifecycle_state"]:
            findings.append({"code":"LIFECYCLE_STATE_MISMATCH","lifecycle_fingerprint":d["lifecycle_fingerprint"]})
        state=life["lifecycle_state"]; decision=d["decision"]
        allowed={
            "DEFERRED":{"AUTHORIZE_RETENTION_REVIEW","AUTHORIZE_PRESERVATION"},
            "ACKNOWLEDGED":{"AUTHORIZE_PRESERVATION"},
            "ESCALATED":{"AUTHORIZE_ESCALATION"},
            "OPEN":set(),
        }.get(state,set())
        if decision not in allowed:
            findings.append({"code":"DECISION_STATE_MISMATCH","lifecycle_fingerprint":d["lifecycle_fingerprint"],"decision":decision,"lifecycle_state":state})
        if d["execution_permitted"] is not False or d["execution_performed"] is not False or d["execution_gate_closed"] is not True or d["automatic_repair_performed"] is not False:
            findings.append({"code":"EXECUTION_GATE_VIOLATION","decision_fingerprint":d["decision_fingerprint"]})
        if d.get("environmental_conclusion") is not None or d.get("regulatory_conclusion") is not None or d.get("enforcement_action") is not None:
            findings.append({"code":"UNEXPECTED_GOVERNANCE_CONCLUSION","decision_fingerprint":d["decision_fingerprint"]})
    for fp, ls in life_by_fp.items():
        bound=decisions_by_lifecycle.get(fp,[])
        if len(bound)>1: findings.append({"code":"MULTIPLE_DECISIONS_FOR_LIFECYCLE","lifecycle_fingerprint":fp,"count":len(bound)})
    # Every lifecycle is expected to have one authorization record.
    for fp in life_by_fp:
        if fp not in decisions_by_lifecycle:
            findings.append({"code":"UNAUTHORIZED_LIFECYCLE","lifecycle_fingerprint":fp})
    # Detect decision references that point at a known monitor/review but no exact lifecycle.
    for d in valid_d:
        if d["lifecycle_fingerprint"] not in life_by_fp and d["monitor_fingerprint"] in monitor_fps:
            findings.append({"code":"LIFECYCLE_BINDING_MISMATCH","decision_fingerprint":d["decision_fingerprint"]})
        if d["lifecycle_fingerprint"] not in life_by_fp and d["review_fingerprint"] in review_fps:
            findings.append({"code":"LIFECYCLE_BINDING_MISMATCH","decision_fingerprint":d["decision_fingerprint"]})
    return sorted(findings, key=lambda x: (x.get("code",""), str(x)))

def reconcile_retention_authorizations(
    lifecycles: list[Mapping[str, Any]],
    decisions: list[Mapping[str, Any]],
    *,
    expected_decision_count: int | None = None,
) -> dict[str, Any]:
    if not isinstance(lifecycles, list) or not isinstance(decisions, list):
        raise ValueError("INPUTS_MUST_BE_LISTS")
    if expected_decision_count is not None and (not isinstance(expected_decision_count,int) or expected_decision_count < 0):
        raise ValueError("INVALID_EXPECTED_DECISION_COUNT")
    findings=_findings(lifecycles,decisions)
    if expected_decision_count is not None and expected_decision_count != len(decisions):
        findings.append({"code":"DECISION_COUNT_MISMATCH","expected":expected_decision_count,"observed":len(decisions)})
        findings=sorted(findings,key=lambda x:(x.get("code",""),str(x)))
    state="CONTROL_REQUIRED" if findings else ("NO_HISTORY" if not lifecycles and not decisions else "RECONCILED")
    payload={
        "policy_version":POLICY_VERSION,
        "lifecycle_policy_version":LIFECYCLE_POLICY_VERSION,
        "decision_policy_version":DECISION_POLICY_VERSION,
        "state":state,
        "lifecycle_count":len(lifecycles),
        "decision_count":len(decisions),
        "findings":findings,
        "read_only":True,
        "human_governed":True,
        "execution_gate_closed":True,
        "execution_permitted":False,
        "execution_performed":False,
        "automatic_repair_performed":False,
        "interpretation":"RETENTION_AUTHORIZATION_RECONCILIATION_ONLY",
        "environmental_conclusion":None,
        "regulatory_conclusion":None,
        "enforcement_action":None,
        "emergency_action":None,
    }
    return dict(payload,reconciliation_fingerprint=fingerprint(payload))

def validate_retention_authorization_reconciliation(result: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(result,Mapping): raise ValueError("INVALID_RETENTION_AUTHORIZATION_RECONCILIATION")
    required=("policy_version","state","lifecycle_count","decision_count","findings","read_only","human_governed","execution_gate_closed","execution_permitted","execution_performed","automatic_repair_performed","reconciliation_fingerprint")
    for key in required:
        if key not in result: raise ValueError(f"MISSING_{key.upper()}")
    if result["policy_version"] != POLICY_VERSION: raise ValueError("INVALID_RECONCILIATION_POLICY")
    if result["state"] not in ("NO_HISTORY","RECONCILED","CONTROL_REQUIRED"): raise ValueError("INVALID_RECONCILIATION_STATE")
    if result["read_only"] is not True or result["human_governed"] is not True: raise ValueError("INVALID_GOVERNANCE_CONTROLS")
    if result["execution_gate_closed"] is not True or result["execution_permitted"] is not False or result["execution_performed"] is not False: raise ValueError("EXECUTION_MUST_REMAIN_CLOSED")
    if result["automatic_repair_performed"] is not False: raise ValueError("AUTOMATIC_REPAIR_FORBIDDEN")
    payload=dict(result); supplied=payload.pop("reconciliation_fingerprint")
    if fingerprint(payload) != supplied: raise ValueError("RECONCILIATION_FINGERPRINT_MISMATCH")
    return dict(result)
