"""Phase 117 — read-only integrity monitoring for authorization-history retention evidence."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_history import reconcile_authorization_history

POLICY_VERSION = "phase117-v1"
REGISTRY_POLICY_VERSION = "phase116-v1"

def build_authorization_retention_monitor(
    registry_records: Sequence[Mapping[str, Any]], *, expected_count: int | None = None, observed_at: str
) -> dict[str, Any]:
    """Assess Phase 116 retention evidence without repairing or mutating it."""
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
            findings.append({"code": "REGISTRY_POLICY_MISMATCH", "index": index, "observed": str(record.get("registry_policy_version"))})
        snapshots.append({k: v for k, v in record.items() if k != "registry_policy_version"})

    history = reconcile_authorization_history(snapshots)
    findings.extend(dict(item) for item in history["findings"])

    for index, snapshot in enumerate(snapshots):
        decisions = snapshot.get("decisions") if isinstance(snapshot, Mapping) else None
        if isinstance(decisions, list):
            for decision in decisions:
                if isinstance(decision, Mapping) and (
                    decision.get("execution_permitted") is not False
                    or decision.get("execution_performed") is not False
                ):
                    findings.append({"code": "EXECUTION_GATE_VIOLATION", "index": index, "sequence": snapshot.get("sequence")})

    fingerprints = [r.get("snapshot_fingerprint") for r in records if isinstance(r, Mapping)]
    for value, count in Counter(x for x in fingerprints if x is not None).items():
        if count > 1:
            findings.append({"code": "DUPLICATE_SNAPSHOT_FINGERPRINT", "identity": str(value)})

    findings.sort(key=lambda x: (x.get("code", ""), str(x.get("index", "")), str(x.get("sequence", "")), str(x.get("identity", ""))))

    if not records and not findings:
        state, recommendation = "NO_HISTORY", "REVIEW_RETENTION"
    elif findings:
        state, recommendation = "CONTROL_REQUIRED", "PRESERVE_AND_ESCALATE"
    else:
        state, recommendation = "RETENTION_HEALTHY", "NO_RETENTION_ACTION"

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
        "findings": findings,
        "retention_recommendation": recommendation,
        "read_only": True,
        "automatic_repair_performed": False,
        "execution_gate_closed": True,
        "interpretation": "AUTHORIZATION_RETENTION_INTEGRITY_MONITORING",
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
    }
    return dict(payload, monitor_fingerprint=fingerprint(payload))

def monitor_registry(registry: Any, *, observed_at: str | None = None) -> dict[str, Any]:
    """Read a Phase 116 registry and produce retention-health evidence."""
    if not hasattr(registry, "list") or not hasattr(registry, "count"):
        raise ValueError("INVALID_AUTHORIZATION_HISTORY_REGISTRY")
    records = registry.list()
    count = registry.count()
    timestamp = observed_at or datetime.now(timezone.utc).isoformat()
    return build_authorization_retention_monitor(records, expected_count=count, observed_at=timestamp)
