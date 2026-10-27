"""Tests for NEMA-AGORA indicator measurement evidence contracts."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from nema_agora.indicator_evidence import IndicatorEvidenceError, validate_measurement_record


def _registry():
    path = Path(__file__).resolve().parents[1] / "nema_agora" / "indicator_registry.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _indicator(indicator_id="ENV-DETECT-002"):
    return next(item for item in _registry()["indicators"] if item["id"] == indicator_id)


def _valid_record():
    return {
        "indicator_id": "ENV-DETECT-002",
        "status": "measured",
        "period_start": "2026-01-01",
        "period_end": "2026-01-31",
        "value": 80.0,
        "unit": "percent",
        "numerator": 8,
        "denominator": 10,
        "source_record_ids": ["reference-set-v1", "alerts-export-v2"],
        "evidence_reference": "evidence://pilot/evaluation-2026-01",
        "evidence_sha256": "a" * 64,
        "method_version": "satellite-evaluation-1.0.0",
        "calculated_at": "2026-02-01T12:00:00Z",
    }


def test_valid_measured_record_returns_caveated_validation_summary():
    result = validate_measurement_record(_valid_record(), _indicator())
    assert result["valid"] is True
    assert result["evidence_authenticity_verified"] is False
    assert result["reviewer_identity_authenticated"] is False


def test_verified_measurement_requires_independent_review():
    record = _valid_record()
    record["status"] = "verified"
    with pytest.raises(IndicatorEvidenceError, match="reviewer_id"):
        validate_measurement_record(record, _indicator())


def test_verified_measurement_accepts_complete_independent_review_fields():
    record = _valid_record()
    record.update({
        "status": "verified",
        "reviewer_id": "reviewer-01",
        "reviewed_at": "2026-02-02T09:30:00+03:00",
        "review_outcome": "accepted",
        "reviewer_independent": True,
    })
    assert validate_measurement_record(record, _indicator())["status"] == "verified"


@pytest.mark.parametrize("field,value", [
    ("evidence_sha256", "not-a-digest"),
    ("evidence_reference", ""),
    ("method_version", ""),
    ("source_record_ids", []),
    ("calculated_at", "2026-02-01T12:00:00"),
    ("period_start", "2026-02-31"),
])
def test_required_provenance_fields_fail_closed(field, value):
    record = _valid_record()
    record[field] = value
    with pytest.raises(IndicatorEvidenceError):
        validate_measurement_record(record, _indicator())


def test_numerator_denominator_must_match_reported_percent():
    record = _valid_record()
    record["value"] = 95.0
    with pytest.raises(IndicatorEvidenceError, match="does not match numerator/denominator"):
        validate_measurement_record(record, _indicator())


def test_invalid_percent_and_reversed_reporting_period_are_rejected():
    record = _valid_record()
    record["value"] = 101
    record["period_start"] = "2026-02-01"
    record["period_end"] = "2026-01-01"
    with pytest.raises(IndicatorEvidenceError):
        validate_measurement_record(record, _indicator())


def test_indicator_id_and_unit_must_match_registry():
    record = _valid_record()
    record["indicator_id"] = "COM-ONBOARD-001"
    with pytest.raises(IndicatorEvidenceError):
        validate_measurement_record(record, _indicator())


def test_duplicate_source_record_ids_are_rejected():
    record = _valid_record()
    record["source_record_ids"] = ["same-id", "same-id"]
    with pytest.raises(IndicatorEvidenceError):
        validate_measurement_record(record, _indicator())

def test_uploaded_artifact_bytes_must_match_declared_digest():
    record = _valid_record()
    payload = b"independently reviewed reference evidence\n"
    record["evidence_sha256"] = hashlib.sha256(payload).hexdigest()
    result = validate_measurement_record(record, _indicator(), evidence_bytes=payload)
    assert result["evidence_artifact_bytes_verified"] is True
    assert result["evidence_authenticity_verified"] is False


def test_uploaded_artifact_digest_mismatch_is_rejected():
    record = _valid_record()
    with pytest.raises(IndicatorEvidenceError, match="does not match evidence_sha256"):
        validate_measurement_record(record, _indicator(), evidence_bytes=b"different artifact")


def test_missing_artifact_bytes_are_not_claimed_as_verified():
    result = validate_measurement_record(_valid_record(), _indicator())
    assert result["evidence_artifact_bytes_verified"] is False

