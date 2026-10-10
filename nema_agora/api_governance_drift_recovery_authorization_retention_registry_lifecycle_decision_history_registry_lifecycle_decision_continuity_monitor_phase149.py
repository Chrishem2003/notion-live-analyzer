"""Phase 149 — integrity monitoring for Phase 148 continuity history."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_phase147 import (
    POLICY_VERSION as CONTINUITY_POLICY_VERSION,
    reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity,
    validate_authorization_history_registry_decision_history_lifecycle_decision_snapshot,
)
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_phase148 import (
    POLICY_VERSION as REGISTRY_POLICY_VERSION,
    AuthorizationHistoryRegistryDecisionHistoryLifecycleDecisionContinuityRegistry,
)

POLICY_VERSION = "phase149-v1"
STATES = ("NO_HISTORY", "CONTINUITY_HEALTHY", "CONTROL_REQUIRED")
RECOMMENDATIONS = (
    "REVIEW_CONTINUITY",
    "NO_CONTINUITY_ACTION",
    "PRESERVE_AND_ESCALATE",
)


def build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(
    registry_records: Sequence[Mapping[str, Any]],
    *,
    expected_count: int | None = None,
    observed_at: str,
) -> dict[str, Any]:
    if not isinstance(registry_records, Sequence) or isinstance(registry_records, (str, bytes)):
        raise ValueError("INVALID_REGISTRY_RECORDS")
    if expected_count is not None and (
        not isinstance(expected_count, int) or isinstance(expected_count, bool) or expected_count < 0
    ):
        raise ValueError("INVALID_EXPECTED_COUNT")
    if not isinstance(observed_at, str) or not observed_at.strip():
        raise ValueError("OBSERVATION_TIME_REQUIRED")

    findings: list[dict[str, Any]] = []
    valid_records: list[dict[str, Any]] = []
    for index, record in enumerate(registry_records):
        try:
            valid_records.append(
                validate_authorization_history_registry_decision_history_lifecycle_decision_snapshot(record)
            )
        except ValueError as exc:
            findings.append({"code": "INVALID_REGISTRY_RECORD", "index": index, "reason": str(exc)})

    if expected_count is not None and len(registry_records) != expected_count:
        findings.append({
            "code": "REGISTRY_COUNT_MISMATCH",
            "expected": expected_count,
            "observed": len(registry_records),
        })

    if len(valid_records) != len(registry_records):
        findings.append({
            "code": "INVALID_REGISTRY_RECORD_COUNT",
            "expected": len(registry_records),
            "valid": len(valid_records),
        })

    continuity = reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity(
        registry_records
    )
    for finding in continuity["findings"]:
        findings.append({"code": "CONTINUITY_" + str(finding.get("code", "UNKNOWN")), **{
            key: value for key, value in finding.items() if key != "code"
        }})

    findings.sort(
        key=lambda x: (
            str(x.get("code", "")),
            str(x.get("index", "")),
            str(x.get("sequence", "")),
        )
    )

    if not registry_records:
        state = "NO_HISTORY"
        recommendation = "REVIEW_CONTINUITY"
    elif findings:
        state = "CONTROL_REQUIRED"
        recommendation = "PRESERVE_AND_ESCALATE"
    else:
        state = "CONTINUITY_HEALTHY"
        recommendation = "NO_CONTINUITY_ACTION"

    payload = {
        "policy_version": POLICY_VERSION,
        "registry_policy_version": REGISTRY_POLICY_VERSION,
        "continuity_policy_version": CONTINUITY_POLICY_VERSION,
        "observed_at": observed_at,
        "state": state,
        "recommendation": recommendation,
        "registry_count": len(registry_records),
        "valid_registry_count": len(valid_records),
        "expected_count": expected_count,
        "findings": findings,
        "human_governed": True,
        "read_only": True,
        "automatic_repair_performed": False,
        "execution_gate_closed": True,
        "execution_permitted": False,
        "execution_performed": False,
        "interpretation": "AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY_LIFECYCLE_DECISION_CONTINUITY_INTEGRITY",
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
        "emergency_action": None,
    }
    return dict(payload, monitor_fingerprint=fingerprint(payload))


def monitor_registry(
    registry: AuthorizationHistoryRegistryDecisionHistoryLifecycleDecisionContinuityRegistry,
    *,
    observed_at: str,
    expected_count: int | None = None,
) -> dict[str, Any]:
    return build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(
        registry.list(),
        expected_count=registry.count() if expected_count is None else expected_count,
        observed_at=observed_at,
    )


def validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(report, Mapping):
        raise ValueError("INVALID_MONITOR")
    required = (
        "policy_version", "registry_policy_version", "continuity_policy_version",
        "observed_at", "state", "recommendation", "registry_count",
        "valid_registry_count", "expected_count", "findings", "human_governed",
        "read_only", "automatic_repair_performed", "execution_gate_closed",
        "execution_permitted", "execution_performed", "monitor_fingerprint",
    )
    for key in required:
        if key not in report:
            raise ValueError("MONITOR_FIELDS_REQUIRED")
    if report["policy_version"] != POLICY_VERSION:
        raise ValueError("MONITOR_POLICY_VIOLATION")
    if report["registry_policy_version"] != REGISTRY_POLICY_VERSION:
        raise ValueError("REGISTRY_POLICY_VIOLATION")
    if report["continuity_policy_version"] != CONTINUITY_POLICY_VERSION:
        raise ValueError("CONTINUITY_POLICY_VIOLATION")
    if report["state"] not in STATES or report["recommendation"] not in RECOMMENDATIONS:
        raise ValueError("MONITOR_STATE_OR_RECOMMENDATION_INVALID")
    if report["human_governed"] is not True or report["read_only"] is not True:
        raise ValueError("MONITOR_GOVERNANCE_VIOLATION")
    if report["automatic_repair_performed"] is not False:
        raise ValueError("AUTOMATIC_REPAIR_FORBIDDEN")
    if (
        report["execution_gate_closed"] is not True
        or report["execution_permitted"] is not False
        or report["execution_performed"] is not False
    ):
        raise ValueError("EXECUTION_GATE_VIOLATION")
    if not isinstance(report["findings"], list):
        raise ValueError("INVALID_FINDINGS")
    if report["registry_count"] < 0 or report["valid_registry_count"] < 0:
        raise ValueError("INVALID_COUNTS")
    if report["valid_registry_count"] > report["registry_count"]:
        raise ValueError("VALID_COUNT_EXCEEDS_REGISTRY_COUNT")
    payload = dict(report)
    supplied = payload.pop("monitor_fingerprint")
    if fingerprint(payload) != supplied:
        raise ValueError("MONITOR_FINGERPRINT_MISMATCH")
    return dict(report)
