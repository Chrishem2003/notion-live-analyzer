"""Phase 65 — read-only reconciliation of spatial review queue and human-review audit evidence."""
from __future__ import annotations
import hashlib, json, re
from typing import Any, Mapping

POLICY_VERSION = "phase65-v1"
ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")

def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")).hexdigest()

def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(ID_RE.fullmatch(value.strip()))

def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA_RE.fullmatch(value.strip().lower()))

def _finding(code: str, review_item_id: str | None = None, detail: str | None = None) -> dict[str, Any]:
    item = {"code": code}
    if review_item_id:
        item["review_item_id"] = review_item_id
    if detail:
        item["detail"] = detail
    item["fingerprint"] = fingerprint(item)
    return item

def reconcile_spatial_reviews(queue_items: list[Mapping[str, Any]], audit_events: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Reconcile immutable queue records with immutable human-review audit events.

    The function is read-only: it derives findings and never mutates either source.
    """
    findings: list[dict[str, Any]] = []
    queue_by_id: dict[str, Mapping[str, Any]] = {}
    audit_by_id: dict[str, list[Mapping[str, Any]]] = {}

    if not isinstance(queue_items, list) or not isinstance(audit_events, list):
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED", "findings": [_finding("INVALID_RECONCILIATION_INPUT")]}

    for item in queue_items:
        if not isinstance(item, Mapping):
            findings.append(_finding("INVALID_QUEUE_RECORD"))
            continue
        item_id = item.get("review_item_id")
        if not _valid_id(item_id):
            findings.append(_finding("INVALID_QUEUE_REVIEW_ITEM_ID"))
            continue
        if item_id in queue_by_id:
            findings.append(_finding("DUPLICATE_QUEUE_ITEM", item_id))
            continue
        queue_by_id[item_id] = item

    for event in audit_events:
        if not isinstance(event, Mapping):
            findings.append(_finding("INVALID_AUDIT_EVENT"))
            continue
        item_id = event.get("review_item_id")
        if not _valid_id(item_id):
            findings.append(_finding("INVALID_AUDIT_REVIEW_ITEM_ID"))
            continue
        audit_by_id.setdefault(item_id, []).append(event)

    for item_id, item in queue_by_id.items():
        events = audit_by_id.get(item_id, [])
        if not events:
            findings.append(_finding("MISSING_REVIEW", item_id))
            continue
        if len(events) > 1:
            findings.append(_finding("DUPLICATE_REVIEW", item_id))
        if item.get("queue_state") != "QUEUED":
            findings.append(_finding("STALE_REVIEW", item_id, "Queue record is no longer QUEUED."))
        queue_fp = str(item.get("record_fingerprint", "")).strip().lower()
        if not _valid_sha(queue_fp):
            findings.append(_finding("INVALID_QUEUE_FINGERPRINT", item_id))
            continue
        for event in events:
            source_fp = str(event.get("source_queue_fingerprint", "")).strip().lower()
            if not _valid_sha(source_fp) or source_fp != queue_fp:
                findings.append(_finding("REVIEW_FINGERPRINT_MISMATCH", item_id))
            if event.get("candidate_id") != item.get("candidate_id"):
                findings.append(_finding("REVIEW_IDENTITY_MISMATCH", item_id, "candidate_id differs from queue record."))

    for item_id, events in audit_by_id.items():
        if item_id not in queue_by_id:
            for _ in events:
                findings.append(_finding("ORPHAN_REVIEW", item_id))

    findings.sort(key=lambda x: (x.get("code", ""), x.get("review_item_id", ""), x["fingerprint"]))
    summary = {
        "queue_items": len(queue_by_id),
        "audit_events": sum(len(v) for v in audit_by_id.values()),
        "reviewed_items": sum(1 for v in audit_by_id.values() if v),
        "missing_reviews": sum(x["code"] == "MISSING_REVIEW" for x in findings),
        "orphan_reviews": sum(x["code"] == "ORPHAN_REVIEW" for x in findings),
        "duplicate_reviews": sum(x["code"] == "DUPLICATE_REVIEW" for x in findings),
        "fingerprint_mismatches": sum(x["code"] == "REVIEW_FINGERPRINT_MISMATCH" for x in findings),
        "stale_reviews": sum(x["code"] == "STALE_REVIEW" for x in findings),
        "identity_mismatches": sum(x["code"] == "REVIEW_IDENTITY_MISMATCH" for x in findings),
    }
    result = {
        "policy_version": POLICY_VERSION,
        "state": "CONTROL_REQUIRED" if findings else "RECONCILED",
        "findings": findings,
        "summary": summary,
        "interpretation": {
            "status": "HUMAN_REVIEW_REQUIRED" if findings else "RECONCILIATION_COMPLETE",
            "environmental_conclusion": None,
            "regulatory_conclusion": None,
            "violation": None,
            "enforcement_action": None,
        },
    }
    result["reconciliation_fingerprint"] = fingerprint(result)
    return result
