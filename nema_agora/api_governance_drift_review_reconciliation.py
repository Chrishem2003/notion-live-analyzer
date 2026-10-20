"""Phase 106 — governance drift review audit reconciliation and integrity."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Mapping, Sequence

from .api_audit_binding import fingerprint
from .api_governance_drift_review_registry import validate_review_audit

POLICY_VERSION = "phase106-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def reconcile_drift_reviews(
    queue_items: Sequence[Mapping[str, Any]],
    drift_events: Sequence[Mapping[str, Any]],
    review_audits: Sequence[Mapping[str, Any]],
    registry_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Reconcile queued drift, source drift events, audits, and persisted rows.

    Inputs are evidence snapshots; this function never writes or repairs them.
    """
    findings: list[dict[str, str]] = []
    def finding(code: str, key: str, identity: str = "") -> None:
        findings.append({"code": code, "key": key, "identity": identity})

    def keyed(items: Sequence[Mapping[str, Any]], key: str, label: str):
        values = [item.get(key) for item in items]
        if any(not isinstance(value, str) or not value for value in values):
            finding("INVALID_IDENTITY", label)
        counts = Counter(value for value in values if isinstance(value, str) and value)
        for value, count in counts.items():
            if count > 1:
                finding("DUPLICATE_RECORD", label, value)
        return {item.get(key): item for item in items if isinstance(item.get(key), str) and item.get(key)}

    queues = keyed(queue_items, "review_id", "queue.review_id")
    drifts = keyed(drift_events, "drift_id", "drift.drift_id")
    audits = keyed(review_audits, "review_id", "audit.review_id")
    stored = keyed(registry_records, "review_id", "registry.review_id")

    for review_id, item in queues.items():
        drift_id = item.get("drift_id")
        drift = drifts.get(drift_id)
        if drift is None:
            finding("MISSING_DRIFT_EVENT", "queue.drift_id", str(review_id))
        else:
            if item.get("drift_fingerprint") != drift.get("drift_fingerprint"):
                finding("DRIFT_FINGERPRINT_MISMATCH", "queue.drift_fingerprint", str(review_id))
            if item.get("baseline_snapshot_id") != drift.get("baseline_snapshot_id"):
                finding("BASELINE_SNAPSHOT_MISMATCH", "queue.baseline_snapshot_id", str(review_id))
            if item.get("current_snapshot_id") != drift.get("current_snapshot_id"):
                finding("CURRENT_SNAPSHOT_MISMATCH", "queue.current_snapshot_id", str(review_id))

    for review_id, audit in audits.items():
        item = queues.get(review_id)
        if item is None:
            finding("ORPHAN_REVIEW_AUDIT", "audit.review_id", str(review_id))
        else:
            for field in ("drift_id", "drift_fingerprint", "baseline_snapshot_id", "current_snapshot_id"):
                if audit.get(field) != item.get(field):
                    finding("QUEUE_AUDIT_BINDING_MISMATCH", field, str(review_id))
        try:
            validate_review_audit(audit)
        except (ValueError, TypeError, KeyError):
            finding("REVIEW_AUDIT_INVALID", "audit_fingerprint", str(review_id))

        persisted = stored.get(review_id)
        if persisted is None:
            finding("MISSING_PERSISTED_AUDIT", "registry.review_id", str(review_id))
        else:
            for field in (
                "audit_id", "drift_id", "drift_fingerprint",
                "baseline_snapshot_id", "current_snapshot_id",
                "reviewer_actor_id", "reviewer_role", "outcome",
                "reviewed_at", "audit_fingerprint",
            ):
                if persisted.get(field) != audit.get(field):
                    finding("PERSISTED_AUDIT_MISMATCH", field, str(review_id))
            if persisted.get("policy_version") != "phase105-v1":
                finding("PERSISTED_POLICY_MISMATCH", "policy_version", str(review_id))

    for review_id in stored.keys() - audits.keys():
        finding("ORPHAN_PERSISTED_AUDIT", "registry.review_id", str(review_id))
    for review_id in audits.keys() - queues.keys():
        # Already reported as orphan above; keep a single canonical finding.
        pass
    for drift_id in drifts.keys() - {item.get("drift_id") for item in queue_items}:
        finding("UNQUEUED_DRIFT_EVENT", "drift_id", str(drift_id))

    findings.sort(key=lambda item: (item["code"], item["key"], item["identity"]))
    state = "CONTROL_REQUIRED" if findings else "RECONCILED"
    payload = {
        "policy_version": POLICY_VERSION,
        "state": state,
        "findings": findings,
        "queue_count": len(queue_items),
        "drift_event_count": len(drift_events),
        "review_audit_count": len(review_audits),
        "persisted_audit_count": len(registry_records),
        "interpretation": "GOVERNANCE_DRIFT_REVIEW_AUDIT_RECONCILIATION",
        "read_only": True,
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
    }
    payload["reconciliation_fingerprint"] = fingerprint(payload)
    return payload
