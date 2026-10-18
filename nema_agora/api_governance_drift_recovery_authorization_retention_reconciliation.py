"""Phase 119 — reconciliation of retention-health human reviews."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_review import (
    validate_retention_monitor,
    validate_retention_review,
)

POLICY_VERSION = "phase119-v1"


def reconcile_retention_reviews(
    monitor_reports: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    *,
    expected_review_count: int | None = None,
) -> dict[str, Any]:
    if not isinstance(monitor_reports, Sequence) or isinstance(monitor_reports, (str, bytes)):
        raise ValueError("INVALID_MONITOR_REPORTS")
    if not isinstance(reviews, Sequence) or isinstance(reviews, (str, bytes)):
        raise ValueError("INVALID_RETENTION_REVIEWS")
    if expected_review_count is not None and (
        not isinstance(expected_review_count, int)
        or isinstance(expected_review_count, bool)
        or expected_review_count < 0
    ):
        raise ValueError("INVALID_EXPECTED_REVIEW_COUNT")

    findings: list[dict[str, Any]] = []
    valid_monitors: list[Mapping[str, Any]] = []
    valid_reviews: list[Mapping[str, Any]] = []

    for index, report in enumerate(monitor_reports):
        try:
            valid_monitors.append(validate_retention_monitor(report))
        except ValueError as exc:
            findings.append({"code": "INVALID_MONITOR", "index": index, "reason": str(exc)})

    for index, review in enumerate(reviews):
        try:
            valid_reviews.append(validate_retention_review(review))
        except ValueError as exc:
            findings.append({"code": "INVALID_REVIEW", "index": index, "reason": str(exc)})

    monitor_by_fp = {}
    for index, report in enumerate(valid_monitors):
        fp = report["monitor_fingerprint"]
        if fp in monitor_by_fp:
            findings.append({"code": "DUPLICATE_MONITOR_FINGERPRINT", "identity": fp})
        monitor_by_fp[fp] = report

    review_by_fp = {}
    review_fingerprints = set()
    for index, review in enumerate(valid_reviews):
        fp = review["review_fingerprint"]
        if fp in review_fingerprints:
            findings.append({"code": "DUPLICATE_REVIEW_FINGERPRINT", "identity": fp})
        review_fingerprints.add(fp)
        monitor_fp = review["monitor_fingerprint"]
        if monitor_fp in review_by_fp:
            findings.append({"code": "MULTIPLE_REVIEWS_FOR_MONITOR", "identity": monitor_fp})
        review_by_fp[monitor_fp] = review

    for monitor_fp, monitor in monitor_by_fp.items():
        review = review_by_fp.get(monitor_fp)
        if review is None:
            findings.append({"code": "UNREVIEWED_MONITOR", "identity": monitor_fp})
            continue
        if review["monitor_state"] != monitor["state"]:
            findings.append({"code": "MONITOR_STATE_MISMATCH", "identity": monitor_fp})
        if review["retention_recommendation"] != monitor["retention_recommendation"]:
            findings.append({"code": "RECOMMENDATION_MISMATCH", "identity": monitor_fp})
        if review["monitor_fingerprint"] != monitor_fp:
            findings.append({"code": "MONITOR_BINDING_MISMATCH", "identity": monitor_fp})
        if monitor["state"] == "RETENTION_HEALTHY" and review["outcome"] != "ACKNOWLEDGED":
            findings.append({"code": "HEALTHY_OUTCOME_MISMATCH", "identity": monitor_fp})
        if monitor["state"] in ("NO_HISTORY", "CONTROL_REQUIRED") and review["outcome"] == "ACKNOWLEDGED":
            findings.append({"code": "UNSAFE_ACKNOWLEDGEMENT", "identity": monitor_fp})
        if monitor["state"] == "CONTROL_REQUIRED" and review["outcome"] not in (
            "REVIEW_RETENTION", "PRESERVE_AND_ESCALATE", "ESCALATED"
        ):
            findings.append({"code": "CONTROL_OUTCOME_MISMATCH", "identity": monitor_fp})

    for monitor_fp in review_by_fp:
        if monitor_fp not in monitor_by_fp:
            findings.append({"code": "ORPHAN_REVIEW", "identity": monitor_fp})

    if expected_review_count is not None and expected_review_count != len(reviews):
        findings.append({
            "code": "REVIEW_COUNT_MISMATCH",
            "expected": expected_review_count,
            "observed": len(reviews),
        })

    findings.sort(key=lambda item: (item.get("code", ""), str(item.get("identity", "")), str(item.get("index", ""))))
    state = "CONTROL_REQUIRED" if findings else ("RECONCILED" if monitor_reports or reviews else "NO_HISTORY")
    payload = {
        "policy_version": POLICY_VERSION,
        "state": state,
        "monitor_count": len(monitor_reports),
        "review_count": len(reviews),
        "valid_monitor_count": len(valid_monitors),
        "valid_review_count": len(valid_reviews),
        "expected_review_count": expected_review_count,
        "findings": findings,
        "read_only": True,
        "human_governed": True,
        "execution_gate_closed": True,
        "automatic_repair_performed": False,
        "interpretation": "RETENTION_REVIEW_RECONCILIATION",
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
    }
    return dict(payload, reconciliation_fingerprint=fingerprint(payload))


def validate_retention_reconciliation(result: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "policy_version", "state", "monitor_count", "review_count",
        "valid_monitor_count", "valid_review_count", "findings",
        "read_only", "human_governed", "execution_gate_closed",
        "automatic_repair_performed", "reconciliation_fingerprint",
    )
    if not isinstance(result, Mapping):
        raise ValueError("INVALID_RECONCILIATION")
    for key in required:
        if key not in result:
            raise ValueError(f"MISSING_{key.upper()}")
    if result["policy_version"] != POLICY_VERSION:
        raise ValueError("INVALID_RECONCILIATION_POLICY")
    if result["state"] not in ("RECONCILED", "CONTROL_REQUIRED", "NO_HISTORY"):
        raise ValueError("INVALID_RECONCILIATION_STATE")
    if result["read_only"] is not True or result["human_governed"] is not True:
        raise ValueError("INVALID_RECONCILIATION_CONTROLS")
    if result["execution_gate_closed"] is not True or result["automatic_repair_performed"] is not False:
        raise ValueError("INVALID_RECONCILIATION_EXECUTION_CONTROLS")
    if not isinstance(result["findings"], list):
        raise ValueError("INVALID_RECONCILIATION_FINDINGS")
    payload = dict(result)
    supplied = payload.pop("reconciliation_fingerprint")
    if fingerprint(payload) != supplied:
        raise ValueError("RECONCILIATION_FINGERPRINT_MISMATCH")
    return dict(result)
