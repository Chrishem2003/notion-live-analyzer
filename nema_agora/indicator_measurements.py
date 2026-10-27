"""Validation contract for evidence-backed NEMA-AGORA indicator measurements.

This module validates records in memory only. It does not persist measurements,
contact providers, or imply that a target has been achieved.
"""
from __future__ import annotations

from datetime import date, datetime
from math import isfinite
from typing import Any, Mapping

VALID_STATUSES = {"not_started", "in_progress", "measured", "verified", "blocked"}
REQUIRED_BASE_FIELDS = {
    "indicator_id",
    "definition_version",
    "reporting_period_start",
    "reporting_period_end",
    "reporting_timezone",
    "status",
}


class IndicatorMeasurementError(ValueError):
    """Raised when an indicator measurement fails the published contract."""


def validate_indicator_measurement(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of a valid record, otherwise raise a useful error.

    Numeric values may be zero, but missing values must be represented as null or
    omitted rather than silently converted to zero. Verified records require
    explicit evidence, reviewer identity, and a timezone-aware verification time.
    """
    if not isinstance(record, Mapping):
        raise IndicatorMeasurementError("Measurement must be an object.")
    missing = sorted(REQUIRED_BASE_FIELDS - set(record))
    if missing:
        raise IndicatorMeasurementError("Missing required fields: " + ", ".join(missing))

    result = dict(record)
    for key in ("indicator_id", "definition_version", "reporting_timezone"):
        value = result.get(key)
        if not isinstance(value, str) or not value.strip():
            raise IndicatorMeasurementError(f"{key} must be a non-empty string.")

    start_raw, end_raw = result.get("reporting_period_start"), result.get("reporting_period_end")
    try:
        start = date.fromisoformat(start_raw)
        end = date.fromisoformat(end_raw)
    except (TypeError, ValueError) as exc:
        raise IndicatorMeasurementError("Reporting period dates must use YYYY-MM-DD.") from exc
    if end < start:
        raise IndicatorMeasurementError("Reporting period end cannot precede its start.")

    status_value = result.get("status")
    if status_value not in VALID_STATUSES:
        raise IndicatorMeasurementError(f"status must be one of: {', '.join(sorted(VALID_STATUSES))}.")

    value = result.get("value")
    if value is not None:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise IndicatorMeasurementError("value must be a finite number or null.")
        if value < 0:
            raise IndicatorMeasurementError("value cannot be negative.")

    for key in ("numerator", "denominator"):
        part = result.get(key)
        if part is not None and (
            isinstance(part, bool) or not isinstance(part, (int, float))
            or not isfinite(part) or part < 0
        ):
            raise IndicatorMeasurementError(f"{key} must be a finite non-negative number or null.")
    numerator, denominator = result.get("numerator"), result.get("denominator")
    if numerator is not None and denominator is not None and numerator > denominator:
        raise IndicatorMeasurementError("numerator cannot exceed denominator.")

    for key in ("source_refs", "evidence_refs", "exclusions"):
        items = result.get(key, [])
        if not isinstance(items, list) or any(not isinstance(item, str) or not item.strip() for item in items):
            raise IndicatorMeasurementError(f"{key} must be a list of non-empty strings.")
        result[key] = items

    if status_value in {"measured", "verified"}:
        if value is None:
            raise IndicatorMeasurementError(f"{status_value} measurements require a numeric value.")
        if not result["source_refs"]:
            raise IndicatorMeasurementError(f"{status_value} measurements require source_refs.")
        if not isinstance(result.get("calculation_method"), str) or not result["calculation_method"].strip():
            raise IndicatorMeasurementError(f"{status_value} measurements require calculation_method.")
    if status_value == "verified":
        if not result["evidence_refs"]:
            raise IndicatorMeasurementError("verified measurements require evidence_refs.")
        if not isinstance(result.get("reviewer_id"), str) or not result["reviewer_id"].strip():
            raise IndicatorMeasurementError("verified measurements require reviewer_id.")
        verified_at = result.get("verified_at")
        if not isinstance(verified_at, str) or not verified_at.strip():
            raise IndicatorMeasurementError("verified measurements require verified_at.")
        try:
            parsed = datetime.fromisoformat(verified_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise IndicatorMeasurementError("verified_at must be an ISO-8601 timestamp.") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise IndicatorMeasurementError("verified_at must include a timezone.")
    return result
