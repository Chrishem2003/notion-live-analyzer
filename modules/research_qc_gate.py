"""Fail-closed research QC and downstream handoff gate.

This is a pure validation layer: it does not change Notion records or claim a
human review occurred. Callers must persist the returned decision and evidence.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any, Mapping


QC_VERIFIED = "🟢 Verified"
QC_ANOMALOUS = "🔴 Anomalous"
QC_PENDING = "🟡 Pending"

# Required before a result can be reviewed as scientifically ready. Values must
# come from the record; this module never invents missing provenance.
_REQUIRED_PROVENANCE = (
    "Record Classification",
    "Measurement Unit",
    "Protocol",
    "Protocol ID/Version",
    "Raw Source Reference",
    "Source Dataset Version",
)


def _present(value: Any) -> bool:
    """Recognize meaningful values, including Notion-shaped property payloads.

    A non-empty wrapper object is not itself evidence: for example,
    {"type": "relation", "relation": []} must not satisfy Protocol.
    """
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        property_keys = (
            "relation", "rich_text", "title", "files", "people", "multi_select",
            "select", "date", "url", "number", "email", "phone_number",
            "checkbox", "formula", "rollup", "status",
        )
        present_property_keys = [key for key in property_keys if key in value]
        if present_property_keys:
            return any(_present(value[key]) for key in present_property_keys)
        return any(_present(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_present(item) for item in value)
    return True


def _valid_review_date(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
        return False
    try:
        date.fromisoformat(normalized)
    except ValueError:
        return False
    return True


def evaluate_research_gate(record: Mapping[str, Any], action: str) -> dict[str, Any]:
    """Return a deterministic allow/block decision for a research workflow action.

    Supported actions: approve_qc, analyze, report, close. A QC approval requires
    complete provenance plus reviewer, review date, and evidence. Reporting and
    closure additionally require the stored QC status to be Verified. Anomalous
    or Pending QC can never pass a downstream gate.
    """
    if not isinstance(record, Mapping):
        raise TypeError("record must be a mapping")
    if action not in {"approve_qc", "analyze", "report", "close"}:
        raise ValueError(f"unsupported research gate action: {action}")

    blockers: list[str] = []
    for field in _REQUIRED_PROVENANCE:
        if not _present(record.get(field)):
            blockers.append(f"Missing required provenance: {field}")

    classification = record.get("Record Classification")
    if classification not in {"Demo", "Synthetic/Test", "Real Research"}:
        blockers.append("Record Classification must be explicit and recognized")

    qc_status = record.get("Analysis Status.")
    if action in {"report", "close"}:
        if qc_status != QC_VERIFIED:
            if qc_status == QC_ANOMALOUS:
                blockers.append("Anomalous QC must be investigated and dispositioned before reporting or closure")
            else:
                blockers.append("QC must be Verified before reporting or closure")

    if action == "approve_qc":
        if not _present(record.get("QC Reviewer")):
            blockers.append("Missing QC Reviewer")
        if not _valid_review_date(record.get("QC Review Date")):
            blockers.append("QC Review Date must be a valid ISO date (YYYY-MM-DD)")
        if not _present(record.get("QC Evidence")):
            blockers.append("Missing QC Evidence")
        if qc_status == QC_ANOMALOUS:
            blockers.append("Anomalous QC cannot be approved without a documented correction and new review")
        elif qc_status == QC_VERIFIED:
            blockers.append("Record is already marked Verified; do not silently overwrite the prior decision")
        elif qc_status not in (None, "", QC_PENDING):
            blockers.append("Unknown QC status cannot be approved; normalize it through a documented review")

    if action in {"report", "close"}:
        if not _present(record.get("QC Reviewer")):
            blockers.append("Missing required review evidence: QC Reviewer")
        if not _valid_review_date(record.get("QC Review Date")):
            blockers.append("QC Review Date must be a valid ISO date (YYYY-MM-DD)")
        if not _present(record.get("QC Evidence")):
            blockers.append("Missing required review evidence: QC Evidence")

    return {
        "allowed": not blockers,
        "action": action,
        "qc_status": qc_status if _present(qc_status) else QC_PENDING,
        "blockers": blockers,
        "requires_human_review": action in {"approve_qc", "report", "close"},
        "decision": ("READY_FOR_HUMAN_REVIEW" if action == "approve_qc" else "ALLOW") if not blockers else "BLOCK",
        "limitations": [
            "Validation only; no record was changed and no external service was called.",
            "The caller must persist this decision with actor, timestamp, record identity, and evidence.",
        ],
    }
