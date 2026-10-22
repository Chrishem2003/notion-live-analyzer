"""Phase 104 — validated governance-drift human review and audit binding."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Mapping

from .api_audit_binding import fingerprint

OUTCOMES = ("ACKNOWLEDGED", "INVESTIGATE", "NO_DRIFT_CONFIRMED", "ESCALATED")
ROLES = ("coordinator", "admin")
POLICY_VERSION = "phase104-v2"
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SEVERITIES = {"HIGH", "MEDIUM", "NONE"}


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _validate_queue_item(item: Mapping[str, Any]) -> None:
    for key in ("review_id", "drift_id", "baseline_snapshot_id", "current_snapshot_id"):
        if not isinstance(item.get(key), str) or not _ID_RE.fullmatch(item[key]):
            raise ValueError("INVALID_REVIEW_ITEM_ID")
    if not isinstance(item.get("drift_fingerprint"), str) or not _SHA256_RE.fullmatch(item["drift_fingerprint"]):
        raise ValueError("INVALID_REVIEW_ITEM_FINGERPRINT")
    if item.get("severity") not in _SEVERITIES:
        raise ValueError("INVALID_REVIEW_ITEM_SEVERITY")
    priority = item.get("priority")
    if not isinstance(priority, int) or isinstance(priority, bool) or not 0 <= priority <= 100:
        raise ValueError("INVALID_REVIEW_ITEM_PRIORITY")
    payload = {
        "drift_id": item["drift_id"],
        "drift_fingerprint": item["drift_fingerprint"],
        "baseline_snapshot_id": item["baseline_snapshot_id"],
        "current_snapshot_id": item["current_snapshot_id"],
        "severity": item["severity"],
        "priority": priority,
    }
    expected_id = "API-DRIFT-REVIEW-" + fingerprint(payload)[:24]
    if item["review_id"] != expected_id:
        raise ValueError("REVIEW_ITEM_ID_MISMATCH")


def review_drift(
    item: Mapping[str, Any],
    *,
    actor_id: str,
    role: str,
    outcome: str,
    reviewed_at: str,
) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        raise ValueError("INVALID_REVIEW_ITEM")
    if item.get("state") != "QUEUED":
        raise ValueError("REVIEW_ITEM_NOT_QUEUED")
    if role not in ROLES:
        raise ValueError("REVIEWER_NOT_AUTHORIZED")
    if not isinstance(actor_id, str) or not _ID_RE.fullmatch(actor_id):
        raise ValueError("INVALID_REVIEWER_ID")
    if outcome not in OUTCOMES:
        raise ValueError("INVALID_REVIEW_OUTCOME")
    if not _valid_timestamp(reviewed_at):
        raise ValueError("INVALID_REVIEW_TIME")
    _validate_queue_item(item)

    payload = {
        "review_id": item["review_id"],
        "drift_id": item["drift_id"],
        "drift_fingerprint": item["drift_fingerprint"],
        "baseline_snapshot_id": item["baseline_snapshot_id"],
        "current_snapshot_id": item["current_snapshot_id"],
        "reviewer_actor_id": actor_id,
        "reviewer_role": role,
        "outcome": outcome,
        "reviewed_at": reviewed_at.strip(),
    }
    audit_fingerprint = fingerprint(payload)
    return dict(
        payload,
        audit_id="API-DRIFT-REVIEW-AUDIT-" + audit_fingerprint[:24],
        audit_fingerprint=audit_fingerprint,
        state="REVIEW_RECORDED",
        policy_version=POLICY_VERSION,
        interpretation="API_GOVERNANCE_DRIFT_HUMAN_REVIEW",
        environmental_conclusion=None,
        regulatory_conclusion=None,
        violation=None,
        enforcement_action=None,
    )
