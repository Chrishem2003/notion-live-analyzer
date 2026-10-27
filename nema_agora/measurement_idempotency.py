"""Deterministic payload and retry contract for future measurement writes.

This module is deliberately storage-agnostic. It helps an API/RPC compare retry
payloads, but does not reserve keys, persist records, or make concurrent writes
safe by itself. The database must enforce a unique idempotency key transactionally.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")


class MeasurementIdempotencyError(ValueError):
    """Raised when an idempotency request is malformed."""


def canonical_payload_sha256(payload: Mapping[str, Any]) -> str:
    """Hash a JSON-compatible payload deterministically.

    Keys are sorted and separators are fixed. NaN/Infinity and non-JSON values
    are rejected rather than being encoded inconsistently across runtimes.
    Array order is preserved because it may be semantically meaningful.
    """
    if not isinstance(payload, Mapping):
        raise MeasurementIdempotencyError("Payload must be a JSON object.")
    try:
        encoded = json.dumps(
            dict(payload),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise MeasurementIdempotencyError(
            "Payload must contain only finite, UTF-8 JSON-compatible values."
        ) from exc
    return hashlib.sha256(encoded).hexdigest()


def classify_idempotent_retry(
    idempotency_key: str,
    payload: Mapping[str, Any],
    existing_payload_sha256: str | None,
) -> dict[str, str]:
    """Classify a retry against a previously stored payload digest.

    Results are advisory until paired with a database uniqueness constraint and
    an atomic insert/audit transaction. Never use this function as check-then-insert
    concurrency control.
    """
    if not isinstance(idempotency_key, str) or not _KEY.fullmatch(idempotency_key):
        raise MeasurementIdempotencyError(
            "idempotency_key must be 1-128 safe ASCII characters."
        )
    digest = canonical_payload_sha256(payload)
    if existing_payload_sha256 is None:
        decision = "new"
    elif (
        not isinstance(existing_payload_sha256, str)
        or not _SHA256.fullmatch(existing_payload_sha256)
    ):
        raise MeasurementIdempotencyError(
            "Stored payload digest must be a 64-character SHA-256 value."
        )
    elif digest == existing_payload_sha256.lower():
        decision = "replay"
    else:
        decision = "conflict"
    return {
        "idempotency_key": idempotency_key,
        "payload_sha256": digest,
        "decision": decision,
    }
