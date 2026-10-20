"""Phase 109 — read-only reconciliation-history integrity monitoring and recovery evidence."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .api_audit_binding import fingerprint
from .api_governance_drift_reconciliation_history import build_snapshot_history

POLICY_VERSION = "phase109-v1"
REGISTRY_POLICY_VERSION = "phase108-v1"


def build_history_integrity_monitor(
    registry_records: Sequence[Mapping[str, Any]],
    *,
    expected_count: int | None = None,
    observed_at: str,
) -> dict[str, Any]:
    """Assess persisted Phase 108 rows without changing them or repairing history."""
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
        findings.append({
            "code": "REGISTRY_COUNT_MISMATCH",
            "expected": expected_count,
            "observed": len(records),
        })

    snapshots: list[Mapping[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            findings.append({"code": "INVALID_REGISTRY_RECORD", "index": index})
            continue
        if record.get("registry_policy_version") != REGISTRY_POLICY_VERSION:
            findings.append({
                "code": "REGISTRY_POLICY_MISMATCH",
                "index": index,
                "observed": str(record.get("registry_policy_version")),
            })
        snapshots.append({
            key: value for key, value in record.items()
            if key != "registry_policy_version"
        })

    history = build_snapshot_history(snapshots)
    for finding in history["findings"]:
        findings.append(dict(finding))

    fingerprints = [
        record.get("snapshot_fingerprint")
        for record in records if isinstance(record, Mapping)
    ]
    for value, count in Counter(item for item in fingerprints if item is not None).items():
        if count > 1:
            findings.append({"code": "DUPLICATE_SNAPSHOT_FINGERPRINT", "identity": str(value)})

    # A stored row must be represented by a valid snapshot, not merely be JSON-shaped.
    valid_count = history.get("valid_snapshot_count", 0)
    if valid_count != len(records):
        findings.append({
            "code": "REGISTRY_RECORD_VALIDATION_COUNT_MISMATCH",
            "registry_record_count": len(records),
            "valid_snapshot_count": valid_count,
        })

    findings.sort(key=lambda item: (
        item.get("code", ""), str(item.get("index", "")),
        str(item.get("sequence", "")), str(item.get("identity", "")),
    ))
    if not records and not findings:
        state = "NO_HISTORY"
        recommendation = "REVIEW_BACKUP"
    elif findings:
        state = "CONTROL_REQUIRED"
        recommendation = "PRESERVE_AND_ESCALATE"
    else:
        state = "MONITORING_CLEAR"
        recommendation = "NO_RECOVERY_ACTION"

    payload = {
        "policy_version": POLICY_VERSION,
        "state": state,
        "observed_at": observed_at,
        "registry_policy_version": REGISTRY_POLICY_VERSION,
        "registry_record_count": len(records),
        "expected_count": expected_count,
        "valid_snapshot_count": valid_count,
        "history_state": history["state"],
        "history_fingerprint": history["history_fingerprint"],
        "findings": findings,
        "recovery_recommendation": recommendation,
        "recovery_required": state == "CONTROL_REQUIRED",
        "automatic_repair_performed": False,
        "read_only": True,
        "interpretation": "RECONCILIATION_HISTORY_INTEGRITY_MONITORING",
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
    }
    return dict(payload, monitor_fingerprint=fingerprint(payload))


def monitor_registry(registry: Any, *, observed_at: str | None = None) -> dict[str, Any]:
    """Read records and row count from a Phase 108 registry; never write to it."""
    if not hasattr(registry, "list") or not hasattr(registry, "count"):
        raise ValueError("INVALID_HISTORY_REGISTRY")
    records = registry.list()
    count = registry.count()
    timestamp = observed_at or datetime.now(timezone.utc).isoformat()
    return build_history_integrity_monitor(records, expected_count=count, observed_at=timestamp)
