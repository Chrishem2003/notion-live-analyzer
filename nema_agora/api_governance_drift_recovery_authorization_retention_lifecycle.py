"""Phase 120 — lifecycle evaluation for retention human reviews."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_authorization_retention_review import validate_retention_review
from .api_governance_drift_recovery_authorization_retention_reconciliation import validate_retention_reconciliation

POLICY_VERSION = "phase120-v1"
STATES = ("OPEN", "ACKNOWLEDGED", "DEFERRED", "ESCALATED")
OUTCOMES = ("ACKNOWLEDGED", "REVIEW_RETENTION", "PRESERVE_AND_ESCALATE", "ESCALATED")


def evaluate_retention_review_lifecycle(
    review: Mapping[str, Any], *, evaluated_at: str
) -> dict[str, Any]:
    validated = validate_retention_review(review)
    if not isinstance(evaluated_at, str) or not evaluated_at.strip():
        raise ValueError("EVALUATION_TIME_REQUIRED")
    try:
        datetime.fromisoformat(evaluated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_EVALUATION_TIME") from exc

    mapping = {
        "ACKNOWLEDGED": "ACKNOWLEDGED",
        "REVIEW_RETENTION": "DEFERRED",
        "PRESERVE_AND_ESCALATE": "ESCALATED",
        "ESCALATED": "ESCALATED",
    }
    payload = {
        "policy_version": POLICY_VERSION,
        "monitor_fingerprint": validated["monitor_fingerprint"],
        "review_fingerprint": validated["review_fingerprint"],
        "review_outcome": validated["outcome"],
        "lifecycle_state": mapping[validated["outcome"]],
        "evaluated_at": evaluated_at,
        "human_governed": True,
        "automatic_repair_performed": False,
        "decision_executed": False,
        "execution_gate_closed": True,
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
    }
    return dict(payload, lifecycle_fingerprint=fingerprint(payload))


def validate_retention_lifecycle(lifecycle: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "policy_version", "monitor_fingerprint", "review_fingerprint",
        "review_outcome", "lifecycle_state", "evaluated_at",
        "human_governed", "automatic_repair_performed", "decision_executed",
        "execution_gate_closed", "lifecycle_fingerprint",
    )
    if not isinstance(lifecycle, Mapping):
        raise ValueError("INVALID_RETENTION_LIFECYCLE")
    for key in required:
        if key not in lifecycle:
            raise ValueError(f"MISSING_{key.upper()}")
    payload = dict(lifecycle)
    supplied = payload.pop("lifecycle_fingerprint")
    if fingerprint(payload) != supplied:
        raise ValueError("RETENTION_LIFECYCLE_FINGERPRINT_MISMATCH")
    if lifecycle["policy_version"] != POLICY_VERSION:
        raise ValueError("INVALID_LIFECYCLE_POLICY")
    if lifecycle["review_outcome"] not in OUTCOMES or lifecycle["lifecycle_state"] not in STATES:
        raise ValueError("INVALID_LIFECYCLE_VALUE")
    if lifecycle["human_governed"] is not True or lifecycle["automatic_repair_performed"] is not False:
        raise ValueError("INVALID_LIFECYCLE_CONTROLS")
    if lifecycle["decision_executed"] is not False or lifecycle["execution_gate_closed"] is not True:
        raise ValueError("INVALID_EXECUTION_CONTROLS")
    return dict(lifecycle)


def build_retention_review_lifecycle(
    reconciliation: Mapping[str, Any],
    reviews: Sequence[Mapping[str, Any]],
    *,
    evaluated_at: str,
) -> dict[str, Any]:
    rec = validate_retention_reconciliation(reconciliation)
    if rec["state"] != "RECONCILED":
        raise ValueError("RECONCILIATION_MUST_BE_RECONCILED")
    if not isinstance(reviews, Sequence) or isinstance(reviews, (str, bytes)) or not reviews:
        raise ValueError("RETENTION_REVIEWS_REQUIRED")
    lifecycles = [
        evaluate_retention_review_lifecycle(review, evaluated_at=evaluated_at)
        for review in reviews
    ]
    payload = {
        "policy_version": POLICY_VERSION,
        "evaluated_at": evaluated_at,
        "reconciliation_fingerprint": rec["reconciliation_fingerprint"],
        "lifecycle_count": len(lifecycles),
        "lifecycles": lifecycles,
        "human_governed": True,
        "automatic_repair_performed": False,
        "execution_gate_closed": True,
        "interpretation": "RETENTION_REVIEW_LIFECYCLE_GOVERNANCE",
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
    }
    return dict(payload, lifecycle_fingerprint=fingerprint(payload))


def validate_retention_lifecycle_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "policy_version", "evaluated_at", "reconciliation_fingerprint",
        "lifecycle_count", "lifecycles", "human_governed",
        "automatic_repair_performed", "execution_gate_closed",
        "lifecycle_fingerprint",
    )
    if not isinstance(bundle, Mapping):
        raise ValueError("INVALID_LIFECYCLE_BUNDLE")
    for key in required:
        if key not in bundle:
            raise ValueError(f"MISSING_{key.upper()}")
    if bundle["policy_version"] != POLICY_VERSION:
        raise ValueError("INVALID_BUNDLE_POLICY")
    if bundle["human_governed"] is not True or bundle["automatic_repair_performed"] is not False:
        raise ValueError("INVALID_BUNDLE_CONTROLS")
    if bundle["execution_gate_closed"] is not True:
        raise ValueError("EXECUTION_GATE_MUST_BE_CLOSED")
    if not isinstance(bundle["lifecycles"], list) or bundle["lifecycle_count"] != len(bundle["lifecycles"]):
        raise ValueError("LIFECYCLE_COUNT_MISMATCH")
    for lifecycle in bundle["lifecycles"]:
        validate_retention_lifecycle(lifecycle)
    payload = dict(bundle)
    supplied = payload.pop("lifecycle_fingerprint")
    if fingerprint(payload) != supplied:
        raise ValueError("RETENTION_LIFECYCLE_BUNDLE_FINGERPRINT_MISMATCH")
    return dict(bundle)
