"""Phase 130 — reconcile retention-registry authorization decisions and execution gates."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_decision import (
    validate_retention_registry_decision,
)
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle import (
    validate_retention_registry_lifecycle,
)

POLICY_VERSION = "phase130-v1"


def reconcile_retention_registry_decisions(
    lifecycles: Sequence[Mapping[str, Any]],
    decisions: Sequence[Mapping[str, Any]],
    *,
    expected_decision_count: int | None = None,
) -> dict[str, Any]:
    if not isinstance(lifecycles, Sequence) or isinstance(lifecycles, (str, bytes)):
        raise ValueError("INVALID_LIFECYCLES")
    if not isinstance(decisions, Sequence) or isinstance(decisions, (str, bytes)):
        raise ValueError("INVALID_DECISIONS")
    if expected_decision_count is not None and (
        not isinstance(expected_decision_count, int)
        or isinstance(expected_decision_count, bool)
        or expected_decision_count < 0
    ):
        raise ValueError("INVALID_EXPECTED_DECISION_COUNT")

    findings: list[dict[str, Any]] = []
    valid_lifecycles: list[dict[str, Any]] = []
    valid_decisions: list[dict[str, Any]] = []

    for index, item in enumerate(lifecycles):
        try:
            valid_lifecycles.append(validate_retention_registry_lifecycle(item))
        except ValueError as exc:
            findings.append({"code": "INVALID_LIFECYCLE", "index": index, "reason": str(exc)})

    for index, item in enumerate(decisions):
        try:
            valid_decisions.append(validate_retention_registry_decision(item))
        except ValueError as exc:
            findings.append({"code": "INVALID_DECISION", "index": index, "reason": str(exc)})

    for key, count in Counter(x["lifecycle_fingerprint"] for x in valid_lifecycles).items():
        if count > 1:
            findings.append({"code": "DUPLICATE_LIFECYCLE_FINGERPRINT", "identity": key})
    for key, count in Counter(x["decision_fingerprint"] for x in valid_decisions).items():
        if count > 1:
            findings.append({"code": "DUPLICATE_DECISION_FINGERPRINT", "identity": key})

    lifecycle_map = {x["lifecycle_fingerprint"]: x for x in valid_lifecycles}
    by_lifecycle: dict[str, list[dict[str, Any]]] = {}
    for decision in valid_decisions:
        by_lifecycle.setdefault(decision["lifecycle_fingerprint"], []).append(decision)

    allowed = {
        "AUTHORIZE_RETENTION_REVIEW": {"DEFERRED"},
        "AUTHORIZE_PRESERVATION": {"ACKNOWLEDGED", "DEFERRED"},
        "AUTHORIZE_ESCALATION": {"ESCALATED"},
    }

    for lifecycle in valid_lifecycles:
        fp = lifecycle["lifecycle_fingerprint"]
        bound = by_lifecycle.get(fp, [])
        if not bound:
            findings.append({"code": "UNAUTHORIZED_LIFECYCLE", "lifecycle_fingerprint": fp})
            continue
        if len(bound) > 1:
            findings.append({
                "code": "MULTIPLE_DECISIONS_FOR_LIFECYCLE",
                "lifecycle_fingerprint": fp,
                "count": len(bound),
            })
        for decision in bound:
            if decision["lifecycle_state"] != lifecycle["lifecycle_state"]:
                findings.append({"code": "LIFECYCLE_STATE_MISMATCH", "lifecycle_fingerprint": fp})
            if decision["monitor_fingerprint"] != lifecycle["monitor_fingerprint"]:
                findings.append({"code": "MONITOR_BINDING_MISMATCH", "lifecycle_fingerprint": fp})
            if decision["review_fingerprint"] != lifecycle["review_fingerprint"]:
                findings.append({"code": "REVIEW_BINDING_MISMATCH", "lifecycle_fingerprint": fp})
            if decision["decision"] not in allowed or lifecycle["lifecycle_state"] not in allowed[decision["decision"]]:
                findings.append({
                    "code": "DECISION_STATE_MISMATCH",
                    "lifecycle_fingerprint": fp,
                    "decision": decision["decision"],
                })
            if (
                decision["human_authorized"] is not True
                or decision["execution_gate_closed"] is not True
                or decision["execution_permitted"] is not False
                or decision["execution_performed"] is not False
                or decision["automatic_repair_performed"] is not False
            ):
                findings.append({"code": "EXECUTION_GATE_VIOLATION", "lifecycle_fingerprint": fp})

    for decision in valid_decisions:
        if decision["lifecycle_fingerprint"] not in lifecycle_map:
            findings.append({
                "code": "ORPHAN_DECISION",
                "lifecycle_fingerprint": decision["lifecycle_fingerprint"],
            })

    if expected_decision_count is not None and expected_decision_count != len(decisions):
        findings.append({
            "code": "DECISION_COUNT_MISMATCH",
            "expected": expected_decision_count,
            "observed": len(decisions),
        })

    findings.sort(key=lambda x: (
        x.get("code", ""),
        str(x.get("lifecycle_fingerprint", "")),
        str(x.get("identity", "")),
        str(x.get("index", "")),
    ))

    state = "CONTROL_REQUIRED" if findings else ("RECONCILED" if valid_lifecycles else "NO_HISTORY")
    payload = {
        "policy_version": POLICY_VERSION,
        "state": state,
        "lifecycle_count": len(lifecycles),
        "valid_lifecycle_count": len(valid_lifecycles),
        "decision_count": len(decisions),
        "valid_decision_count": len(valid_decisions),
        "expected_decision_count": expected_decision_count,
        "findings": findings,
        "read_only": True,
        "human_governed": True,
        "execution_gate_closed": True,
        "execution_permitted": False,
        "execution_performed": False,
        "automatic_repair_performed": False,
        "interpretation": "RETENTION_REGISTRY_AUTHORIZATION_RECONCILIATION",
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
        "emergency_action": None,
    }
    return dict(payload, reconciliation_fingerprint=fingerprint(payload))


def validate_retention_registry_decision_reconciliation(
    result: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(result, Mapping):
        raise ValueError("INVALID_DECISION_RECONCILIATION")
    required = (
        "policy_version", "state", "lifecycle_count", "valid_lifecycle_count",
        "decision_count", "valid_decision_count", "expected_decision_count",
        "findings", "read_only", "human_governed", "execution_gate_closed",
        "execution_permitted", "execution_performed", "automatic_repair_performed",
        "reconciliation_fingerprint",
    )
    for key in required:
        if key not in result:
            raise ValueError(f"MISSING_{key.upper()}")
    if result["policy_version"] != POLICY_VERSION:
        raise ValueError("INVALID_RECONCILIATION_POLICY")
    if result["state"] not in ("NO_HISTORY", "RECONCILED", "CONTROL_REQUIRED"):
        raise ValueError("INVALID_RECONCILIATION_STATE")
    if result["read_only"] is not True or result["human_governed"] is not True:
        raise ValueError("INVALID_GOVERNANCE_CONTROLS")
    if (
        result["execution_gate_closed"] is not True
        or result["execution_permitted"] is not False
        or result["execution_performed"] is not False
    ):
        raise ValueError("EXECUTION_GATE_VIOLATION")
    if result["automatic_repair_performed"] is not False:
        raise ValueError("AUTOMATIC_REPAIR_FORBIDDEN")
    if not isinstance(result["findings"], list):
        raise ValueError("INVALID_FINDINGS")
    payload = dict(result)
    supplied = payload.pop("reconciliation_fingerprint")
    if fingerprint(payload) != supplied:
        raise ValueError("RECONCILIATION_FINGERPRINT_MISMATCH")
    return dict(result)
