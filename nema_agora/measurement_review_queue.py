"""Read-only, authenticated officer queue for canonical indicator measurements."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

REVIEW_ROLES = {"reviewer", "coordinator", "admin"}


class MeasurementReviewQueueError(PermissionError):
    """Raised when a caller cannot view the officer review queue."""


def load_measurement_review_queue(
    *, principal: Mapping[str, Any], repository: Any, limit: int = 100
) -> list[dict[str, Any]]:
    """Load canonical measured records with submission audit history; never writes."""
    if not isinstance(principal, Mapping) or principal.get("authenticated") is not True:
        raise MeasurementReviewQueueError("A verified authenticated officer is required.")
    if not isinstance(principal.get("subject"), str) or not principal["subject"].strip():
        raise MeasurementReviewQueueError("Authenticated officer identity is missing.")
    if principal.get("role") not in REVIEW_ROLES:
        raise MeasurementReviewQueueError("This role cannot view the measurement review queue.")
    rows = repository.list_indicator_measurements(limit=limit, status="measured")
    queue: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("Measurement repository returned an invalid row.")
        measurement_id = row.get("measurement_id")
        if not isinstance(measurement_id, str) or not measurement_id.strip():
            raise ValueError("Canonical measurement row has no measurement ID.")
        events = repository.list_measurement_audit_events(measurement_id)
        submit_events = [event for event in events if event.get("action") == "measurement_submitted"]
        submitters = {event.get("actor_id") for event in submit_events if event.get("actor_id")}
        queue.append({
            "measurement": dict(row),
            "submission_audit_events": events,
            "submission_audit_present": bool(submit_events),
            "submission_actor_ids": sorted(submitters),
            "audit_warning": None if submit_events else "No submission audit event was found; investigate before review.",
            "review_status": "awaiting_independent_review",
            "reviewer_can_self_review": principal["subject"] not in submitters,
            "verification_performed": False,
        })
    return queue


def render_measurement_review_queue(*, principal: Mapping[str, Any], repository: Any) -> None:
    """Render the officer queue in Streamlit. This view is deliberately read-only."""
    import pandas as pd
    import streamlit as st

    st.title("NEMA-AGORA · Indicator Review Queue")
    st.caption("Read-only officer workspace. Reviews and verification are not saved from this screen.")
    try:
        rows = load_measurement_review_queue(principal=principal, repository=repository)
    except Exception as exc:
        st.error(f"Review queue unavailable: {exc}")
        return
    if not rows:
        st.info("No canonical measurements are currently awaiting independent review.")
        return
    frame = pd.DataFrame([{
        "Measurement ID": item["measurement"].get("measurement_id"),
        "Indicator": item["measurement"].get("indicator_id"),
        "Period start": item["measurement"].get("reporting_period_start"),
        "Period end": item["measurement"].get("reporting_period_end"),
        "Value": item["measurement"].get("value"),
        "Unit": item["measurement"].get("unit"),
        "Submitted at": item["measurement"].get("created_at"),
        "Submission audit": "Present" if item["submission_audit_present"] else "MISSING",
        "Review state": item["review_status"].replace("_", " ").title(),
    } for item in rows])
    st.dataframe(frame, use_container_width=True, hide_index=True)
    ids = [item["measurement"]["measurement_id"] for item in rows]
    selected_id = st.selectbox("Inspect measurement", ids, key="nema_measurement_review_selected")
    selected = next(item for item in rows if item["measurement"]["measurement_id"] == selected_id)
    measurement = selected["measurement"]
    if selected["audit_warning"]:
        st.warning(selected["audit_warning"])
    if not selected["reviewer_can_self_review"]:
        st.error("The authenticated officer appears in the submission audit as the submitter. Independent review is not allowed.")
    left, right = st.columns(2)
    with left:
        st.subheader("Canonical measurement")
        st.json({key: measurement.get(key) for key in (
            "measurement_id", "indicator_id", "definition_version", "status", "value", "unit",
            "numerator", "denominator", "reporting_period_start", "reporting_period_end",
            "reporting_timezone", "source_refs", "evidence_refs", "calculation_method", "exclusions", "caveats",
        )})
    with right:
        st.subheader("Immutable submission audit")
        if selected["submission_audit_events"]:
            st.dataframe(pd.DataFrame(selected["submission_audit_events"]), use_container_width=True, hide_index=True)
        else:
            st.info("No submission audit rows returned.")
    st.info("Decision controls are intentionally disabled until a durable, append-only review-event schema and transactional API are approved and tested.")
