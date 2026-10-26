"""Tests for deterministic measurement idempotency preflight contract."""
import copy

import pytest

from nema_agora.measurement_idempotency import (
    MeasurementIdempotencyError,
    canonical_payload_sha256,
    classify_idempotent_retry,
)


def _payload():
    return {
        "measurement_id": "pilot-2026-001",
        "indicator_id": "ENV-DETECT-002",
        "status": "measured",
        "value": 92.5,
        "source_refs": ["site:alpha", "dataset:reference-1"],
    }


def test_canonical_digest_ignores_mapping_key_order():
    payload = _payload()
    reordered = dict(reversed(list(payload.items())))
    assert canonical_payload_sha256(payload) == canonical_payload_sha256(reordered)


def test_canonical_digest_changes_when_value_changes():
    first = _payload()
    changed = copy.deepcopy(first)
    changed["value"] = 92.6
    assert canonical_payload_sha256(first) != canonical_payload_sha256(changed)


def test_array_order_is_preserved():
    first = _payload()
    changed = copy.deepcopy(first)
    changed["source_refs"].reverse()
    assert canonical_payload_sha256(first) != canonical_payload_sha256(changed)


def test_non_finite_numbers_are_rejected():
    payload = _payload()
    payload["value"] = float("nan")
    with pytest.raises(MeasurementIdempotencyError, match="JSON-compatible"):
        canonical_payload_sha256(payload)


def test_non_json_values_are_rejected():
    payload = _payload()
    payload["created_at"] = object()
    with pytest.raises(MeasurementIdempotencyError, match="JSON-compatible"):
        canonical_payload_sha256(payload)


def test_first_submission_is_classified_new():
    result = classify_idempotent_retry("pilot-2026-001", _payload(), None)
    assert result["decision"] == "new"
    assert len(result["payload_sha256"]) == 64


def test_same_payload_retry_is_classified_replay():
    payload = _payload()
    digest = canonical_payload_sha256(payload)
    assert classify_idempotent_retry("pilot-2026-001", payload, digest)["decision"] == "replay"


def test_same_key_with_changed_payload_is_conflict():
    payload = _payload()
    digest = canonical_payload_sha256(payload)
    payload["value"] = 101
    assert classify_idempotent_retry("pilot-2026-001", payload, digest)["decision"] == "conflict"


@pytest.mark.parametrize("key", ["", " ", "../bad", "key with spaces", "x" * 129, "ü-key"])
def test_unsafe_or_invalid_idempotency_keys_are_rejected(key):
    with pytest.raises(MeasurementIdempotencyError, match="idempotency_key"):
        classify_idempotent_retry(key, _payload(), None)


def test_invalid_existing_digest_is_rejected():
    with pytest.raises(MeasurementIdempotencyError, match="Stored payload digest"):
        classify_idempotent_retry("pilot-2026-001", _payload(), "not-a-digest")
