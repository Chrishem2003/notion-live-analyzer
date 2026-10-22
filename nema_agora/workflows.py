"""Read-only NEMA workflows for the governed automation runtime.

These workflows create deterministic review packets from persisted case reads.
They do not mutate cases, close incidents, decide legal compliance, or call an LLM.
The hosting application must inject its authenticated read-only case reader and
the runtime's trusted authorization callback.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from typing import Any

from modules.governed_automation_runtime import GovernedAutomationRuntime, WorkflowSpec

_REQUIRED_TEXT_FIELDS = (
    "case_id",
    "district_or_site",
    "category",
    "severity",
    "status",
    "observation_date",
    "description",
)


def _validate_review_input(inputs: dict[str, Any]) -> None:
    if set(inputs) != {"case_id"}:
        raise ValueError("Inputs must contain only case_id.")
    case_id = inputs.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip() or len(case_id.strip()) > 80:
        raise ValueError("case_id must contain 1–80 non-whitespace characters.")
    if case_id != case_id.strip():
        raise ValueError("case_id must not have leading or trailing whitespace.")


def build_case_review_packet(case_id: str, response: Mapping[str, Any]) -> dict[str, Any]:
    """Convert a trusted API response into a bounded, deterministic review packet."""
    if not isinstance(response, Mapping):
        raise ValueError("Case reader returned an invalid response.")
    record = response.get("record")
    version = response.get("version")
    audit = response.get("audit", [])
    if not isinstance(record, Mapping):
        raise ValueError("Case reader response is missing a valid record.")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValueError("Case reader response has an invalid record version.")
    if not isinstance(audit, list):
        raise ValueError("Case reader response has an invalid audit history.")
    stored_id = record.get("case_id")
    if not isinstance(stored_id, str) or stored_id != case_id:
        raise ValueError("Case reader returned a different case than requested.")

    text_fields: dict[str, str | None] = {}
    missing_fields: list[str] = []
    for field in _REQUIRED_TEXT_FIELDS:
        value = record.get(field)
        if isinstance(value, str):
            cleaned = value.strip()
            text_fields[field] = cleaned[:1500] if cleaned else None
        else:
            text_fields[field] = None
        if not text_fields[field]:
            missing_fields.append(field)

    latitude = record.get("latitude")
    longitude = record.get("longitude")
    latitude_valid = (
        isinstance(latitude, (int, float))
        and not isinstance(latitude, bool)
        and math.isfinite(latitude)
        and -90 <= latitude <= 90
    )
    longitude_valid = (
        isinstance(longitude, (int, float))
        and not isinstance(longitude, bool)
        and math.isfinite(longitude)
        and -180 <= longitude <= 180
    )
    if latitude is None and longitude is None:
        coordinate_state = "not_provided"
    elif latitude_valid and longitude_valid:
        coordinate_state = "present_with_valid_ranges"
    else:
        coordinate_state = "incomplete_or_invalid"

    latest_event_type = None
    if audit:
        latest = audit[-1]
        if isinstance(latest, Mapping):
            event_type = latest.get("event_type")
            if isinstance(event_type, str):
                latest_event_type = event_type[:100]

    return {
        "workflow": "nema.case_review_packet",
        "case_id": case_id,
        "record_version": version,
        "review_status": "human_review_required",
        "source_mode": "read_only",
        "case": text_fields,
        "coordinate_state": coordinate_state,
        "data_quality": {
            "missing_required_fields": missing_fields,
            "required_fields_complete": not missing_fields,
        },
        "audit_summary": {
            "event_count_returned": min(len(audit), 100),
            "latest_event_type": latest_event_type,
        },
        "limitations": [
            "This is a deterministic administrative review aid, not a legal or regulatory determination.",
            "A human reviewer must verify source evidence and applicable policy before taking action.",
            "No case data was changed by this workflow.",
        ],
    }


def register_nema_readonly_workflows(
    runtime: GovernedAutomationRuntime,
    *,
    read_case: Callable[[str], Mapping[str, Any]],
) -> None:
    """Register explicitly allow-listed NEMA read workflows on an existing runtime.

    Authorization is enforced by GovernedAutomationRuntime before the handler runs.
    The injected reader should be the hosting service's authenticated read-only API
    client; this function deliberately does not construct credentials or repositories.
    """
    if not callable(read_case):
        raise TypeError("read_case must be a callable read-only case reader.")

    def review_handler(inputs: dict[str, Any]) -> dict[str, Any]:
        case_id = inputs["case_id"]
        response = read_case(case_id)
        return build_case_review_packet(case_id, response)

    runtime.register(
        WorkflowSpec(
            name="nema.case_review_packet",
            handler=review_handler,
            validate_input=_validate_review_input,
            idempotent=True,
            max_attempts=2,
        )
    )
