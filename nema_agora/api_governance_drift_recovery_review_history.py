"""Phase 112 — deterministic snapshots for recovery-review reconciliation history."""
from __future__ import annotations

import re
from typing import Any, Mapping

from .api_audit_binding import fingerprint

POLICY_VERSION = "phase112-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def build_recovery_review_snapshot(
    reconciliation: Mapping[str, Any], *, captured_at: str, sequence: int,
    predecessor_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Create a deterministic snapshot bound to one valid Phase 111 result."""
    if not isinstance(reconciliation, Mapping):
        raise ValueError("RECONCILIATION_REQUIRED")
    claimed = reconciliation.get("reconciliation_fingerprint")
    if not isinstance(claimed, str) or not _SHA256_RE.fullmatch(claimed):
        raise ValueError("INVALID_RECONCILIATION_FINGERPRINT")
    source = dict(reconciliation)
    source.pop("reconciliation_fingerprint", None)
    if fingerprint(source) != claimed:
        raise ValueError("RECONCILIATION_FINGERPRINT_MISMATCH")
    if reconciliation.get("policy_version") != "phase111-v1":
        raise ValueError("INVALID_RECONCILIATION_POLICY")
    if reconciliation.get("state") not in ("RECONCILED", "CONTROL_REQUIRED"):
        raise ValueError("INVALID_RECONCILIATION_STATE")
    if reconciliation.get("read_only") is not True:
        raise ValueError("RECONCILIATION_NOT_READ_ONLY")
    if not isinstance(captured_at, str) or not captured_at.strip() or len(captured_at) > 128:
        raise ValueError("INVALID_CAPTURED_AT")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise ValueError("INVALID_SEQUENCE")
    if predecessor_fingerprint is not None and (
        not isinstance(predecessor_fingerprint, str) or not _SHA256_RE.fullmatch(predecessor_fingerprint)
    ):
        raise ValueError("INVALID_PREDECESSOR_FINGERPRINT")
    findings = reconciliation.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("INVALID_FINDINGS")
    payload = {
        "policy_version": POLICY_VERSION, "sequence": sequence,
        "captured_at": captured_at.strip(), "reconciliation_fingerprint": claimed,
        "reconciliation_state": reconciliation["state"], "finding_count": len(findings),
        "findings": list(findings), "monitor_report_count": reconciliation.get("monitor_report_count", 0),
        "review_record_count": reconciliation.get("review_record_count", 0),
        "expected_ledger_count": reconciliation.get("expected_ledger_count"),
        "predecessor_fingerprint": predecessor_fingerprint, "read_only": True,
        "source_records_mutated": False, "automatic_repair_performed": False,
        "automatic_recovery_performed": False, "environmental_conclusion": None,
        "regulatory_conclusion": None, "enforcement_action": None,
    }
    digest = fingerprint(payload)
    return dict(payload, snapshot_id="NEMA-AGORA-RECOVERY-REVIEW-SNAPSHOT-" + digest[:24],
                snapshot_fingerprint=digest)


def validate_recovery_review_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute the Phase 112 snapshot identity and fingerprint."""
    if not isinstance(snapshot, Mapping):
        raise ValueError("SNAPSHOT_REQUIRED")
    claimed = snapshot.get("snapshot_fingerprint")
    if not isinstance(claimed, str) or not _SHA256_RE.fullmatch(claimed):
        raise ValueError("INVALID_SNAPSHOT_FINGERPRINT")
    payload = dict(snapshot)
    payload.pop("snapshot_fingerprint", None)
    snapshot_id = payload.pop("snapshot_id", None)
    if fingerprint(payload) != claimed:
        raise ValueError("SNAPSHOT_FINGERPRINT_MISMATCH")
    if snapshot_id != "NEMA-AGORA-RECOVERY-REVIEW-SNAPSHOT-" + claimed[:24]:
        raise ValueError("SNAPSHOT_ID_MISMATCH")
    if snapshot.get("policy_version") != POLICY_VERSION:
        raise ValueError("INVALID_SNAPSHOT_POLICY")
    if not isinstance(snapshot.get("sequence"), int) or isinstance(snapshot.get("sequence"), bool) or snapshot["sequence"] < 1:
        raise ValueError("INVALID_SEQUENCE")
    if snapshot.get("read_only") is not True or snapshot.get("source_records_mutated") is not False:
        raise ValueError("SNAPSHOT_NOT_READ_ONLY")
    return dict(snapshot)


def reconcile_recovery_review_snapshot_history(snapshots: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Validate ordered snapshot history; detect gaps, duplicates and broken links."""
    if not isinstance(snapshots, list) or len(snapshots) > 5000:
        raise ValueError("INVALID_SNAPSHOT_HISTORY")
    findings: list[dict[str, Any]] = []
    valid: list[dict[str, Any]] = []
    for index, item in enumerate(snapshots):
        try:
            valid.append(validate_recovery_review_snapshot(item))
        except (ValueError, TypeError, KeyError) as exc:
            findings.append({"code": "INVALID_SNAPSHOT", "index": index, "reason": str(exc)})
    ordered = sorted(valid, key=lambda item: item["sequence"])
    seen_sequences: set[int] = set()
    seen_ids: set[str] = set()
    seen_fingerprints: set[str] = set()
    previous = None
    for item in ordered:
        seq, sid, fp = item["sequence"], item["snapshot_id"], item["snapshot_fingerprint"]
        if seq in seen_sequences:
            findings.append({"code": "DUPLICATE_SEQUENCE", "sequence": seq})
        if sid in seen_ids:
            findings.append({"code": "DUPLICATE_SNAPSHOT_ID", "snapshot_id": sid})
        if fp in seen_fingerprints:
            findings.append({"code": "DUPLICATE_SNAPSHOT_FINGERPRINT", "snapshot_fingerprint": fp})
        seen_sequences.add(seq); seen_ids.add(sid); seen_fingerprints.add(fp)
        expected_sequence = 1 if previous is None else previous["sequence"] + 1
        expected_predecessor = None if previous is None else previous["snapshot_fingerprint"]
        if seq != expected_sequence:
            findings.append({"code": "SEQUENCE_GAP", "sequence": seq, "expected": expected_sequence})
        if item.get("predecessor_fingerprint") != expected_predecessor:
            findings.append({"code": "PREDECESSOR_MISMATCH", "sequence": seq})
        previous = item
    findings.sort(key=lambda item: (item.get("code", ""), item.get("sequence", item.get("index", -1)), str(item)))
    payload = {
        "policy_version": POLICY_VERSION,
        "state": "NO_HISTORY" if not snapshots else ("CONTROL_REQUIRED" if findings else "HISTORY_RECONCILED"),
        "snapshot_count": len(snapshots), "valid_snapshot_count": len(valid),
        "finding_count": len(findings), "findings": findings, "read_only": True,
        "automatic_repair_performed": False, "automatic_recovery_performed": False,
        "environmental_conclusion": None, "regulatory_conclusion": None, "enforcement_action": None,
    }
    return dict(payload, history_fingerprint=fingerprint(payload))
