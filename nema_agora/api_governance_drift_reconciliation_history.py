"""Phase 107 — deterministic governance drift reconciliation snapshots and history."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Mapping, Sequence

from .api_audit_binding import fingerprint

POLICY_VERSION = "phase107-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_STATES = {"RECONCILED", "CONTROL_REQUIRED"}


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value))


def _reconciliation_is_valid(value: Mapping[str, Any]) -> bool:
    if value.get("policy_version") != "phase106-v1" or value.get("state") != "RECONCILED":
        return False
    claimed = value.get("reconciliation_fingerprint")
    payload = dict(value)
    payload.pop("reconciliation_fingerprint", None)
    return _sha256(claimed) and fingerprint(payload) == claimed


def build_reconciliation_snapshot(
    reconciliation: Mapping[str, Any],
    *,
    captured_at: str,
    sequence: int,
    previous_snapshot_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Build a stable snapshot without changing or persisting the source evidence."""
    if not isinstance(reconciliation, Mapping) or not _reconciliation_is_valid(reconciliation):
        raise ValueError("INVALID_PHASE106_RECONCILIATION")
    if not isinstance(captured_at, str) or not captured_at.strip():
        raise ValueError("CAPTURE_TIME_REQUIRED")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise ValueError("INVALID_SEQUENCE")
    if previous_snapshot_fingerprint is not None and not _sha256(previous_snapshot_fingerprint):
        raise ValueError("INVALID_PREVIOUS_SNAPSHOT_FINGERPRINT")
    if sequence == 1 and previous_snapshot_fingerprint is not None:
        raise ValueError("FIRST_SNAPSHOT_CANNOT_HAVE_PREDECESSOR")
    if sequence > 1 and previous_snapshot_fingerprint is None:
        raise ValueError("PREVIOUS_SNAPSHOT_REQUIRED")

    findings = reconciliation.get("findings")
    if not isinstance(findings, list) or not all(isinstance(item, Mapping) for item in findings):
        raise ValueError("INVALID_RECONCILIATION_FINDINGS")
    source_counts = {
        key: reconciliation.get(key)
        for key in (
            "queue_count", "drift_event_count",
            "review_audit_count", "persisted_audit_count",
        )
    }
    if any(not isinstance(count, int) or isinstance(count, bool) or count < 0 for count in source_counts.values()):
        raise ValueError("INVALID_SOURCE_COUNTS")

    payload = {
        "policy_version": POLICY_VERSION,
        "sequence": sequence,
        "captured_at": captured_at,
        "state": reconciliation["state"],
        "reconciliation_fingerprint": reconciliation["reconciliation_fingerprint"],
        "finding_count": len(findings),
        "findings": [dict(item) for item in findings],
        "source_counts": source_counts,
        "previous_snapshot_fingerprint": previous_snapshot_fingerprint,
        "read_only": True,
        "interpretation": "GOVERNANCE_DRIFT_RECONCILIATION_HISTORY",
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
    }
    snapshot_fingerprint = fingerprint(payload)
    return dict(
        payload,
        snapshot_id="API-DRIFT-RECON-SNAPSHOT-" + snapshot_fingerprint[:24],
        snapshot_fingerprint=snapshot_fingerprint,
    )


def validate_reconciliation_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Validate identity, policy, source binding and deterministic fingerprint."""
    if not isinstance(snapshot, Mapping) or snapshot.get("policy_version") != POLICY_VERSION:
        raise ValueError("INVALID_SNAPSHOT_POLICY")
    required = (
        "snapshot_id", "snapshot_fingerprint", "sequence", "captured_at",
        "state", "reconciliation_fingerprint", "finding_count", "findings",
        "source_counts", "previous_snapshot_fingerprint", "read_only",
    )
    if any(key not in snapshot for key in required):
        raise ValueError("SNAPSHOT_FIELDS_REQUIRED")
    if not _sha256(snapshot.get("snapshot_fingerprint")) or not _sha256(snapshot.get("reconciliation_fingerprint")):
        raise ValueError("INVALID_SNAPSHOT_FINGERPRINT")
    if snapshot.get("state") not in _STATES:
        raise ValueError("INVALID_SNAPSHOT_STATE")
    if not isinstance(snapshot.get("sequence"), int) or isinstance(snapshot.get("sequence"), bool) or snapshot["sequence"] < 1:
        raise ValueError("INVALID_SEQUENCE")
    if not isinstance(snapshot.get("captured_at"), str) or not snapshot["captured_at"].strip():
        raise ValueError("CAPTURE_TIME_REQUIRED")
    if snapshot.get("read_only") is not True:
        raise ValueError("SNAPSHOT_MUST_BE_READ_ONLY")
    if not isinstance(snapshot.get("findings"), list) or snapshot.get("finding_count") != len(snapshot["findings"]):
        raise ValueError("SNAPSHOT_FINDING_COUNT_MISMATCH")
    if not isinstance(snapshot.get("source_counts"), Mapping):
        raise ValueError("INVALID_SOURCE_COUNTS")
    previous = snapshot.get("previous_snapshot_fingerprint")
    if previous is not None and not _sha256(previous):
        raise ValueError("INVALID_PREVIOUS_SNAPSHOT_FINGERPRINT")
    if snapshot["sequence"] == 1 and previous is not None:
        raise ValueError("FIRST_SNAPSHOT_CANNOT_HAVE_PREDECESSOR")
    if snapshot["sequence"] > 1 and previous is None:
        raise ValueError("PREVIOUS_SNAPSHOT_REQUIRED")
    payload = dict(snapshot)
    claimed_fingerprint = payload.pop("snapshot_fingerprint")
    claimed_id = payload.pop("snapshot_id")
    if fingerprint(payload) != claimed_fingerprint:
        raise ValueError("SNAPSHOT_FINGERPRINT_MISMATCH")
    if claimed_id != "API-DRIFT-RECON-SNAPSHOT-" + claimed_fingerprint[:24]:
        raise ValueError("SNAPSHOT_ID_MISMATCH")
    return dict(snapshot)


def build_snapshot_history(snapshots: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Check sequence, identity, fingerprints and predecessor links; never repairs history."""
    if not snapshots:
        payload = {
            "policy_version": POLICY_VERSION,
            "state": "NO_HISTORY",
            "snapshot_count": 0,
            "findings": [],
            "read_only": True,
            "interpretation": "GOVERNANCE_DRIFT_RECONCILIATION_HISTORY",
            "environmental_conclusion": None,
            "regulatory_conclusion": None,
            "enforcement_action": None,
        }
        return dict(payload, history_fingerprint=fingerprint(payload))

    findings: list[dict[str, Any]] = []
    valid: list[dict[str, Any]] = []
    for index, item in enumerate(snapshots):
        try:
            valid.append(validate_reconciliation_snapshot(item))
        except (ValueError, TypeError, KeyError):
            findings.append({"code": "INVALID_SNAPSHOT", "index": index})

    ids = [item.get("snapshot_id") for item in snapshots]
    sequences = [item.get("sequence") for item in snapshots]
    for field, values in (("snapshot_id", ids), ("sequence", sequences)):
        counts = Counter(value for value in values if value is not None)
        for value, count in counts.items():
            if count > 1:
                findings.append({"code": "DUPLICATE_" + field.upper(), "identity": str(value)})

    ordered = sorted(valid, key=lambda item: item["sequence"])
    if ordered and ordered[0]["sequence"] != 1:
        findings.append({"code": "SEQUENCE_START_GAP", "expected": 1, "actual": ordered[0]["sequence"]})
    for previous, current in zip(ordered, ordered[1:]):
        if current["sequence"] != previous["sequence"] + 1:
            findings.append({
                "code": "SEQUENCE_GAP",
                "expected": previous["sequence"] + 1,
                "actual": current["sequence"],
            })
        if current.get("previous_snapshot_fingerprint") != previous.get("snapshot_fingerprint"):
            findings.append({"code": "PREDECESSOR_MISMATCH", "sequence": current["sequence"]})

    findings.sort(key=lambda item: (item["code"], str(item.get("sequence", "")), str(item.get("identity", "")), str(item.get("index", ""))))
    state = "CONTROL_REQUIRED" if findings else "HISTORY_READY"
    payload = {
        "policy_version": POLICY_VERSION,
        "state": state,
        "snapshot_count": len(snapshots),
        "valid_snapshot_count": len(valid),
        "findings": findings,
        "read_only": True,
        "interpretation": "GOVERNANCE_DRIFT_RECONCILIATION_HISTORY",
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
    }
    return dict(payload, history_fingerprint=fingerprint(payload))
