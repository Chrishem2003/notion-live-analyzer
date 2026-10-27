"""Authenticated-boundary preparation for NEMA measurement submissions.

Framework-neutral API service layer. It deliberately does not accept actor identity
or role from the measurement body; callers must pass a principal produced by verified
authentication middleware. This function prepares a request but does not invoke SQL.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nema_agora.measurement_write_contract import (
    MeasurementWriteContractError,
    build_measurement_rpc_request,
)


class MeasurementAuthorizationError(PermissionError):
    """Raised when the authenticated principal cannot submit this measurement."""


def prepare_authenticated_measurement_submission(
    *,
    principal: Mapping[str, Any],
    record: Mapping[str, Any],
    indicator: Mapping[str, Any],
    evidence_bytes: bytes,
    verified_evidence_object: Mapping[str, Any],
    measurement_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    """Prepare an RPC payload using actor claims from trusted auth middleware.

    The HTTP adapter must never construct principal from request JSON. A real
    deployment should use its verified session/JWT dependency and enforce any
    project/indicator scope before calling this function.
    """
    if not isinstance(principal, Mapping) or principal.get("authenticated") is not True:
        raise MeasurementAuthorizationError("A verified authenticated principal is required.")

    actor_id = principal.get("subject")
    role = principal.get("role")
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise MeasurementAuthorizationError("Authenticated principal has no valid subject.")
    if role not in {"submitter", "coordinator", "admin"}:
        raise MeasurementAuthorizationError("This role cannot submit indicator measurements.")

    if not isinstance(indicator, Mapping):
        raise MeasurementWriteContractError("A registry indicator definition is required.")
    indicator_id = indicator.get("id")
    if record.get("indicator_id") != indicator_id:
        raise MeasurementAuthorizationError("The submitted indicator does not match the authorized registry definition.")

    return build_measurement_rpc_request(
        measurement_id=measurement_id,
        idempotency_key=idempotency_key,
        record=record,
        indicator=indicator,
        evidence_bytes=evidence_bytes,
        verified_evidence_object=verified_evidence_object,
        authenticated_actor_id=actor_id,
        authenticated_actor_role=role,
    )
