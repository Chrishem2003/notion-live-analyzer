"""Phase 141 — read-only integrity monitoring for the Phase 140 decision-history registry."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_phase139 import (
    reconcile_authorization_history_registry_decision_history,
)

POLICY_VERSION = "phase141-v1"
REGISTRY_POLICY_VERSION = "phase140-v1"
STATES = ("NO_HISTORY", "RETENTION_REGISTRY_HEALTHY", "CONTROL_REQUIRED")
RECOMMENDATIONS = (
    "REVIEW_RETENTION_REGISTRY",
    "NO_RETENTION_REGISTRY_ACTION",
    "PRESERVE_AND_ESCALATE",
)


def build_authorization_history_registry_decision_history_monitor(
    registry_records: Sequence[Mapping[str, Any]],
    *,
    expected_count: int | None = None,
    observed_at: str,
) -> dict[str, Any]:
    """Inspect Phase 140 evidence without mutation, repair, or execution."""
    if not isinstance(registry_records, Sequence) or isinstance(registry_records, (str, bytes)):
        raise ValueError("INVALID_REGISTRY_RECORDS")
    if expected_count is not None and (
        not isinstance(expected_count, int) or isinstance(expected_count, bool) or expected_count < 0
    ):
        raise ValueError("INVALID_EXPECTED_COUNT")
    if not isinstance(observed_at, str) or not observed_at.strip():
        raise ValueError("OBSERVATION_TIME_REQUIRED")
    try:
        datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_OBSERVATION_TIME") from exc

    records = list(registry_records)
    findings: list[dict[str, Any]] = []
    if expected_count is not None and expected_count != len(records):
        findings.append({"code": "REGISTRY_COUNT_MISMATCH", "expected": expected_count, "observed": len(records)})

    snapshots: list[Mapping[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            findings.append({"code": "INVALID_REGISTRY_RECORD", "index": index})
            continue
        if record.get("registry_policy_version") != REGISTRY_POLICY_VERSION:
            findings.append(
                {"code": "REGISTRY_POLICY_MISMATCH", "index": index, "observed": str(record.get("registry_policy_version"))}
            )
        snapshots.append({k: v for k, v in record.items() if k != "registry_policy_version"})

    history = reconcile_authorization_history_registry_decision_history(snapshots)
    findings.extend(dict(item) for item in history["findings"])
    if history.get("state") == "CONTROL_REQUIRED" and not history.get("findings"):
        findings.append({"code": "HISTORY_CONTROL_STATE_WITHOUT_FINDING"})

    if not records and not findings:
        state, recommendation = "NO_HISTORY", "REVIEW_RETENTION_REGISTRY"
    elif findings:
        state, recommendation = "CONTROL_REQUIRED", "PRESERVE_AND_ESCALATE"
    else:
        state, recommendation = "RETENTION_REGISTRY_HEALTHY", "NO_RETENTION_REGISTRY_ACTION"

    payload = {
        "policy_version": POLICY_VERSION,
        "observed_at": observed_at,
        "registry_policy_version": REGISTRY_POLICY_VERSION,
        "state": state,
        "snapshot_count": len(records),
        "valid_snapshot_count": history.get("valid_snapshot_count", 0),
        "expected_count": expected_count,
        "history_state": history["state"],
        "history_reconciliation_fingerprint": history["reconciliation_fingerprint"],
        "findings": sorted(
            findings,
            key=lambda x: (
                x.get("code", ""),
                str(x.get("index", "")),
                str(x.get("sequence", "")),
                str(x.get("fingerprint", "")),
            ),
        ),
        "retention_registry_recommendation": recommendation,
        "read_only": True,
        "human_governed": True,
        "automatic_repair_performed": False,
        "execution_gate_closed": True,
        "execution_permitted": False,
        "execution_performed": False,
        "interpretation": "AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY_INTEGRITY_MONITORING",
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
        "emergency_action": None,
    }
    return dict(payload, monitor_fingerprint=fingerprint(payload))


def monitor_registry(registry: Any, *, observed_at: str | None = None) -> dict[str, Any]:
    if not hasattr(registry, "list") or not hasattr(registry, "count"):
        raise ValueError("INVALID_AUTHORIZATION_HISTORY_REGISTRY_DECISION_HISTORY_REGISTRY")
    records = registry.list()
    count = registry.count()
    timestamp = observed_at or datetime.now(timezone.utc).isoformat()
    return build_authorization_history_registry_decision_history_monitor(
        records, expected_count=count, observed_at=timestamp
    )


def validate_authorization_history_registry_decision_history_monitor(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(report, Mapping):
        raise ValueError("INVALID_MONITOR_REPORT")
    required = (
        "policy_version", "observed_at", "registry_policy_version", "state",
        "snapshot_count", "valid_snapshot_count", "expected_count", "history_state",
        "history_reconciliation_fingerprint", "findings",
        "retention_registry_recommendation", "read_only", "human_governed",
        "automatic_repair_performed", "execution_gate_closed",
        "execution_permitted", "execution_performed", "monitor_fingerprint",
    )
    for key in required:
        if key not in report:
            raise ValueError("MONITOR_FIELDS_REQUIRED")
    if report["policy_version"] != POLICY_VERSION:
        raise ValueError("MONITOR_POLICY_VIOLATION")
    if report["registry_policy_version"] != REGISTRY_POLICY_VERSION:
        raise ValueError("REGISTRY_POLICY_VIOLATION")
    if report["state"] not in STATES or report["retention_registry_recommendation"] not in RECOMMENDATIONS:
        raise ValueError("MONITOR_STATE_OR_RECOMMENDATION_INVALID")
    expected = {
        "NO_HISTORY": "REVIEW_RETENTION_REGISTRY",
        "RETENTION_REGISTRY_HEALTHY": "NO_RETENTION_REGISTRY_ACTION",
        "CONTROL_REQUIRED": "PRESERVE_AND_ESCALATE",
    }
    if report["retention_registry_recommendation"] != expected[report["state"]]:
        raise ValueError("STATE_RECOMMENDATION_MISMATCH")
    if report["read_only"] is not True or report["human_governed"] is not True:
        raise ValueError("GOVERNANCE_CONTROLS_REQUIRED")
    if report["automatic_repair_performed"] is not False:
        raise ValueError("AUTOMATIC_REPAIR_FORBIDDEN")
    if (
        report["execution_gate_closed"] is not True
        or report["execution_permitted"] is not False
        or report["execution_performed"] is not False
    ):
        raise ValueError("EXECUTION_GATE_VIOLATION")
    payload = dict(report)
    supplied = payload.pop("monitor_fingerprint")
    if fingerprint(payload) != supplied:
        raise ValueError("MONITOR_FINGERPRINT_MISMATCH")
    return dict(report)
