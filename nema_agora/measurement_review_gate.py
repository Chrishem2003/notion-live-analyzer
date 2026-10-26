"""Independent human review gate for NEMA-AGORA indicator measurements.

This module prepares a review decision event in memory only. It never persists data,
changes a measurement's status to verified, or treats a hash as proof of authenticity.
The caller must pass a principal produced by trusted authentication middleware.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

REVIEW_ROLES = {"reviewer", "coordinator", "admin"}
REVIEW_DECISIONS = {"accept_for_verification", "request_correction", "reject"}


class MeasurementReviewError(ValueError):
    """Raised when a review cannot safely be prepared."""


def prepare_measurement_review(
    *,
    principal: Mapping[str, Any],
    measurement: Mapping[str, Any],
    decision: str,
    reviewed_at: str,
    notes: str = "",
) -> dict[str, Any]:
    """Validate independent review and return a non-persistent review event.

    accept_for_verification means the reviewer recommends a separate verification
    action; it does not itself verify the measurement.
    """
    if not isinstance(principal, Mapping) or principal.get("authenticated") is not True:
        raise MeasurementReviewError("A verified authenticated reviewer is required.")
    reviewer_id = principal.get("subject")
    role = principal.get("role")
    if not isinstance(reviewer_id, str) or not reviewer_id.strip():
        raise MeasurementReviewError("Reviewer principal has no valid subject.")
    if role not in REVIEW_ROLES:
        raise MeasurementReviewError("This role cannot review indicator measurements.")
    if not isinstance(measurement, Mapping):
        raise MeasurementReviewError("Measurement must be an object.")
    measurement_id = measurement.get("measurement_id")
    if not isinstance(measurement_id, str) or not measurement_id.strip():
        raise MeasurementReviewError("Measurement ID is required.")
    if measurement.get("status") != "measured":
        raise MeasurementReviewError("Only measured records can enter the independent review gate.")
    submitter_id = measurement.get("submitted_by")
    if not isinstance(submitter_id, str) or not submitter_id.strip():
        raise MeasurementReviewError("Trusted submission actor is required for independence checks.")
    if reviewer_id.strip() == submitter_id.strip():
        raise MeasurementReviewError("The submitter cannot review their own measurement.")
    if decision not in REVIEW_DECISIONS:
        raise MeasurementReviewError("Unsupported measurement review decision.")
    if not isinstance(notes, str) or len(notes) > 2000:
        raise MeasurementReviewError("Review notes must be text of at most 2,000 characters.")
    if decision in {"request_correction", "reject"} and not notes.strip():
        raise MeasurementReviewError("A reason is required for correction or rejection.")
    evidence_refs = measurement.get("evidence_refs")
    if decision == "accept_for_verification" and (
        not isinstance(evidence_refs, list) or not evidence_refs
    ):
        raise MeasurementReviewError("Evidence references are required before recommending verification.")
    if not isinstance(reviewed_at, str) or not reviewed_at.strip():
        raise MeasurementReviewError("Review timestamp is required.")
    try:
        timestamp = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MeasurementReviewError("Review timestamp must be ISO-8601.") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise MeasurementReviewError("Review timestamp must include a timezone.")

    return {
        "event_type": "MEASUREMENT_HUMAN_REVIEW",
        "measurement_id": measurement_id,
        "reviewer_id": reviewer_id.strip(),
        "reviewer_role": role,
        "decision": decision,
        "notes": notes.strip(),
        "reviewed_at": timestamp.isoformat(),
        "measurement_status_before": "measured",
        "measurement_status_after": "measured",
        "verification_performed": False,
        "evidence_authenticity_verified": False,
        "persistence_performed": False,
    }
