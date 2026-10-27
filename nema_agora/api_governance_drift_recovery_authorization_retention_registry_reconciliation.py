"""Phase 127 — reconcile retention-registry integrity monitors with human reviews."""
from __future__ import annotations
from collections import Counter
from typing import Any, Mapping, Sequence
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_registry_monitor import validate_retention_registry_monitor
from .api_governance_drift_recovery_authorization_retention_registry_review import validate_retention_registry_review

POLICY_VERSION = "phase127-v1"

def reconcile_retention_registry_reviews(monitor_reports: Sequence[Mapping[str, Any]], reviews: Sequence[Mapping[str, Any]], *, expected_review_count: int | None = None) -> dict[str, Any]:
    if not isinstance(monitor_reports, Sequence) or isinstance(monitor_reports, (str, bytes)):
        raise ValueError("INVALID_MONITOR_REPORTS")
    if not isinstance(reviews, Sequence) or isinstance(reviews, (str, bytes)):
        raise ValueError("INVALID_REVIEWS")
    if expected_review_count is not None and (not isinstance(expected_review_count, int) or isinstance(expected_review_count, bool) or expected_review_count < 0):
        raise ValueError("INVALID_EXPECTED_REVIEW_COUNT")
    findings: list[dict[str, Any]] = []
    monitors, valid_reviews = [], []
    for index, item in enumerate(monitor_reports):
        try: monitors.append(validate_retention_registry_monitor(item))
        except ValueError as exc: findings.append({"code":"INVALID_MONITOR","index":index,"reason":str(exc)})
    for index, item in enumerate(reviews):
        try: valid_reviews.append(validate_retention_registry_review(item))
        except ValueError as exc: findings.append({"code":"INVALID_REVIEW","index":index,"reason":str(exc)})
    for value, count in Counter(x["monitor_fingerprint"] for x in monitors).items():
        if count > 1: findings.append({"code":"DUPLICATE_MONITOR_FINGERPRINT","identity":value})
    for value, count in Counter(x["review_fingerprint"] for x in valid_reviews).items():
        if count > 1: findings.append({"code":"DUPLICATE_REVIEW_FINGERPRINT","identity":value})
    monitor_map = {x["monitor_fingerprint"]: x for x in monitors}
    by_monitor: dict[str, list[dict[str, Any]]] = {}
    for review in valid_reviews: by_monitor.setdefault(review["monitor_fingerprint"], []).append(review)
    allowed = {
        "ACKNOWLEDGED": lambda s: s == "RETENTION_REGISTRY_HEALTHY",
        "REVIEW_RETENTION_REGISTRY": lambda s: s in ("NO_HISTORY","CONTROL_REQUIRED"),
        "PRESERVE_AND_ESCALATE": lambda s: s == "CONTROL_REQUIRED",
        "ESCALATED": lambda s: s in ("NO_HISTORY","CONTROL_REQUIRED"),
    }
    for monitor in monitors:
        fp, state = monitor["monitor_fingerprint"], monitor["state"]
        bound = by_monitor.get(fp, [])
        if not bound:
            findings.append({"code":"UNREVIEWED_MONITOR","monitor_fingerprint":fp})
            continue
        if len(bound) > 1:
            findings.append({"code":"MULTIPLE_REVIEWS_FOR_MONITOR","monitor_fingerprint":fp,"count":len(bound)})
        for review in bound:
            if review["monitor_state"] != state:
                findings.append({"code":"MONITOR_STATE_MISMATCH","monitor_fingerprint":fp})
            if review["retention_registry_recommendation"] != monitor["retention_registry_recommendation"]:
                findings.append({"code":"RECOMMENDATION_MISMATCH","monitor_fingerprint":fp})
            if not allowed.get(review["outcome"], lambda _: False)(state):
                findings.append({"code":"OUTCOME_STATE_MISMATCH","monitor_fingerprint":fp,"outcome":review["outcome"]})
    for review in valid_reviews:
        if review["monitor_fingerprint"] not in monitor_map:
            findings.append({"code":"ORPHAN_REVIEW","monitor_fingerprint":review["monitor_fingerprint"]})
    if expected_review_count is not None and expected_review_count != len(reviews):
        findings.append({"code":"REVIEW_COUNT_MISMATCH","expected":expected_review_count,"observed":len(reviews)})
    findings.sort(key=lambda x:(x.get("code",""),str(x.get("monitor_fingerprint","")),str(x.get("identity","")),str(x.get("index",""))))
    state = "CONTROL_REQUIRED" if findings else ("RECONCILED" if monitors else "NO_HISTORY")
    payload = {
        "policy_version":POLICY_VERSION,"state":state,"monitor_count":len(monitor_reports),
        "valid_monitor_count":len(monitors),"review_count":len(reviews),"valid_review_count":len(valid_reviews),
        "expected_review_count":expected_review_count,"findings":findings,"read_only":True,
        "human_governed":True,"execution_gate_closed":True,"execution_permitted":False,
        "execution_performed":False,"automatic_repair_performed":False,
        "interpretation":"RETENTION_REGISTRY_HUMAN_REVIEW_RECONCILIATION",
        "environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None,"emergency_action":None,
    }
    return dict(payload, reconciliation_fingerprint=fingerprint(payload))

def validate_retention_registry_review_reconciliation(result: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(result, Mapping): raise ValueError("INVALID_RECONCILIATION")
    required=("policy_version","state","monitor_count","valid_monitor_count","review_count","valid_review_count","expected_review_count","findings","read_only","human_governed","execution_gate_closed","execution_permitted","execution_performed","automatic_repair_performed","reconciliation_fingerprint")
    for key in required:
        if key not in result: raise ValueError("RECONCILIATION_FIELDS_REQUIRED")
    if result["policy_version"] != POLICY_VERSION: raise ValueError("INVALID_RECONCILIATION_POLICY")
    if result["state"] not in ("NO_HISTORY","RECONCILED","CONTROL_REQUIRED"): raise ValueError("INVALID_RECONCILIATION_STATE")
    if result["read_only"] is not True or result["human_governed"] is not True: raise ValueError("INVALID_GOVERNANCE_CONTROLS")
    if result["execution_gate_closed"] is not True or result["execution_permitted"] is not False or result["execution_performed"] is not False: raise ValueError("EXECUTION_GATE_VIOLATION")
    if result["automatic_repair_performed"] is not False: raise ValueError("AUTOMATIC_REPAIR_FORBIDDEN")
    payload=dict(result); supplied=payload.pop("reconciliation_fingerprint")
    if fingerprint(payload) != supplied: raise ValueError("RECONCILIATION_FINGERPRINT_MISMATCH")
    return dict(result)
