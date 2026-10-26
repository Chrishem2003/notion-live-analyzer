"""Trusted-API payload adapter for the proposed NEMA measurement RPC.

This module does not authenticate a user or write to PostgreSQL. The caller must
pass actor identity/role derived from a verified server-side session, and must
enforce role-to-indicator permissions before invoking the RPC.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nema_agora.indicator_evidence import IndicatorEvidenceError, validate_measurement_record


class MeasurementWriteContractError(ValueError):
    """Raised when a client measurement cannot be mapped to the RPC contract."""


_ALLOWED_ROLES = {"submitter", "coordinator", "admin"}


def build_measurement_rpc_request(
    *,
    measurement_id: str,
    idempotency_key: str,
    record: Mapping[str, Any],
    indicator: Mapping[str, Any],
    evidence_bytes: bytes,
    authenticated_actor_id: str,
    authenticated_actor_role: str,
) -> dict[str, Any]:
    """Validate, normalize, and hash a measured record for the SQL RPC.

    The actor arguments are trusted context, not request-body fields. This helper
    cannot authenticate them; only call it after the API has verified the session.
    Evidence bytes are required so the submitted artifact digest is actually checked.
    """
    for label, value in (
        ("measurement_id", measurement_id),
        ("idempotency_key", idempotency_key),
        ("authenticated_actor_id", authenticated_actor_id),
    ):
        if not isinstance(value, str) or not value.strip() or len(value) > 256:
            raise MeasurementWriteContractError(f"{label} must be a non-empty string of at most 256 characters.")
    if "\n" in authenticated_actor_id or "\r" in authenticated_actor_id:
        raise MeasurementWriteContractError("authenticated_actor_id must not contain carriage-return or line-feed characters.")
    if not isinstance(authenticated_actor_role, str) or authenticated_actor_role not in _ALLOWED_ROLES:
        raise MeasurementWriteContractError("Authenticated actor role is not allowed to submit measurements.")
    if not isinstance(evidence_bytes, bytes):
        raise MeasurementWriteContractError("Evidence artifact bytes are required.")
    if not isinstance(record, Mapping):
        raise MeasurementWriteContractError("Measurement record must be an object.")
    for field in ("definition_version", "reporting_timezone"):
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            raise MeasurementWriteContractError(f"{field} is required and must be non-empty text.")

    try:
        validated = validate_measurement_record(record, indicator, evidence_bytes=evidence_bytes)
    except IndicatorEvidenceError as exc:
        raise MeasurementWriteContractError(str(exc)) from exc

    if validated["status"] != "measured":
        raise MeasurementWriteContractError("Only measured records may be submitted; verification is a separate workflow.")

    # Convert the UI evidence contract to the stable database/RPC field names.
    rpc_record = {
        "indicator_id": validated["indicator_id"],
        "definition_version": record["definition_version"],
        "reporting_period_start": validated["period_start"],
        "reporting_period_end": validated["period_end"],
        "reporting_timezone": record.get("reporting_timezone", "UTC"),
        "status": "measured",
        "value": record["value"],
        "unit": record["unit"],
        "numerator": record.get("numerator"),
        "denominator": record.get("denominator"),
        "exclusions": record.get("exclusions", []),
        "source_refs": record["source_record_ids"],
        "evidence_refs": [{
            "reference": record["evidence_reference"],
            "sha256": validated["evidence_sha256"],
        }],
        "calculation_method": record["method_version"],
        "reviewer_id": None,
        "verified_at": None,
        "caveats": record.get("caveats", []),
    }
    return {
        "p_measurement_id": measurement_id,
        "p_idempotency_key": idempotency_key,
        "p_actor_id": authenticated_actor_id,
        "p_actor_role": authenticated_actor_role,
        "p_record": rpc_record,
        "evidence_artifact_bytes_verified": validated["evidence_artifact_bytes_verified"],
        "evidence_authenticity_verified": False,
        "reviewer_identity_authenticated": False,
    }
