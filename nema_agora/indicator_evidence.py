"""Evidence contract for reproducible NEMA-AGORA indicator measurements.

This module validates submitted measurement records. It does not persist records,
authenticate reviewers, or assert that referenced evidence is genuine; those are
separate integration and governance responsibilities.
"""
from __future__ import annotations

from datetime import date, datetime
import hashlib
import math
import re
from typing import Any, Mapping

_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_ALLOWED_MEASUREMENT_STATES = {"measured", "verified"}


class IndicatorEvidenceError(ValueError):
    """Raised when an indicator measurement fails its evidence contract."""


def _parse_date(value: Any, field: str, errors: list[str]) -> date | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is required and must be an ISO date.")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field} must use YYYY-MM-DD.")
        return None


def _parse_timestamp(value: Any, field: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is required and must be an ISO-8601 timestamp.")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} must be an ISO-8601 timestamp.")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        errors.append(f"{field} must include a timezone offset.")
        return None
    return parsed


def validate_measurement_record(
    record: Mapping[str, Any],
    indicator: Mapping[str, Any],
    *,
    evidence_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Validate one measured/verified result against its indicator definition.

    Raises IndicatorEvidenceError with actionable validation errors. If evidence_bytes
    is supplied, its SHA-256 must match the record digest. This proves byte-level
    consistency only; it does not prove source authenticity or reviewer identity.
    """
    if not isinstance(record, Mapping):
        raise IndicatorEvidenceError("Measurement record must be a JSON object.")
    if not isinstance(indicator, Mapping):
        raise IndicatorEvidenceError("Indicator definition must be a JSON object.")

    errors: list[str] = []
    indicator_id = indicator.get("id")
    if record.get("indicator_id") != indicator_id:
        errors.append("indicator_id must match the selected registry indicator.")

    state = record.get("status")
    if state not in _ALLOWED_MEASUREMENT_STATES:
        errors.append("status must be measured or verified; use not_started/in_progress/blocked in the registry.")

    start = _parse_date(record.get("period_start"), "period_start", errors)
    end = _parse_date(record.get("period_end"), "period_end", errors)
    if start is not None and end is not None and start > end:
        errors.append("period_start must be on or before period_end.")

    value = record.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        errors.append("value must be a finite number.")
    elif indicator.get("unit") == "percent" and not 0 <= value <= 100:
        errors.append("percent values must be between 0 and 100.")

    unit = record.get("unit")
    if not isinstance(unit, str) or unit != indicator.get("unit"):
        errors.append("unit must exactly match the registry indicator unit.")

    source_ids = record.get("source_record_ids")
    if (
        not isinstance(source_ids, list)
        or not source_ids
        or any(not isinstance(item, str) or not _ID.fullmatch(item.strip()) for item in source_ids)
        or len(set(source_ids)) != len(source_ids)
    ):
        errors.append("source_record_ids must be a non-empty list of unique valid IDs.")

    evidence_reference = record.get("evidence_reference")
    if not isinstance(evidence_reference, str) or not evidence_reference.strip():
        errors.append("evidence_reference is required.")

    evidence_sha256 = record.get("evidence_sha256")
    if not isinstance(evidence_sha256, str) or not _SHA256.fullmatch(evidence_sha256):
        errors.append("evidence_sha256 must be a 64-character SHA-256 digest.")

    artifact_digest_match = False
    if evidence_bytes is not None:
        if not isinstance(evidence_bytes, bytes):
            errors.append("evidence_bytes must be bytes when supplied.")
        elif isinstance(evidence_sha256, str) and _SHA256.fullmatch(evidence_sha256):
            actual_digest = hashlib.sha256(evidence_bytes).hexdigest()
            artifact_digest_match = actual_digest.lower() == evidence_sha256.lower()
            if not artifact_digest_match:
                errors.append("uploaded evidence artifact SHA-256 does not match evidence_sha256.")

    method_version = record.get("method_version")
    if not isinstance(method_version, str) or not method_version.strip():
        errors.append("method_version is required for reproducibility.")

    _parse_timestamp(record.get("calculated_at"), "calculated_at", errors)

    calculation = str(indicator.get("calculation", "")).lower()
    if "divided by" in calculation or "denominator" in calculation:
        numerator = record.get("numerator")
        denominator = record.get("denominator")
        if (
            isinstance(numerator, bool)
            or not isinstance(numerator, (int, float))
            or not math.isfinite(numerator)
            or numerator < 0
        ):
            errors.append("numerator must be a finite non-negative number for rate/ratio indicators.")
        if (
            isinstance(denominator, bool)
            or not isinstance(denominator, (int, float))
            or not math.isfinite(denominator)
            or denominator <= 0
        ):
            errors.append("denominator must be a finite positive number for rate/ratio indicators.")
        if (
            isinstance(numerator, (int, float))
            and not isinstance(numerator, bool)
            and isinstance(denominator, (int, float))
            and not isinstance(denominator, bool)
            and denominator > 0
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and not math.isclose(value, numerator / denominator * (100 if indicator.get("unit") == "percent" else 1), rel_tol=1e-6, abs_tol=1e-6)
        ):
            errors.append("value does not match numerator/denominator under the indicator's calculation rule.")

    if state == "verified":
        reviewer_id = record.get("reviewer_id")
        if not isinstance(reviewer_id, str) or not _ID.fullmatch(reviewer_id.strip()):
            errors.append("verified measurements require a valid reviewer_id.")
        _parse_timestamp(record.get("reviewed_at"), "reviewed_at", errors)
        if record.get("review_outcome") != "accepted":
            errors.append("verified measurements require review_outcome='accepted'.")
        if record.get("reviewer_independent") is not True:
            errors.append("verified measurements require an explicitly independent reviewer.")
    if errors:
        raise IndicatorEvidenceError("Measurement record rejected: " + " ".join(errors))

    return {
        "valid": True,
        "indicator_id": indicator_id,
        "status": state,
        "period_start": start.isoformat() if start else None,
        "period_end": end.isoformat() if end else None,
        "evidence_sha256": evidence_sha256.lower(),
        "evidence_artifact_bytes_verified": artifact_digest_match,
        "evidence_authenticity_verified": False,
        "reviewer_identity_authenticated": False,
    }
