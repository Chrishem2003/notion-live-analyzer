"""Tests for the evidence-backed NEMA-AGORA measurement contract."""
import pytest

from nema_agora.indicator_measurements import (
    IndicatorMeasurementError,
    validate_indicator_measurement,
)


def base_record(**overrides):
    record = {
        "indicator_id": "DASH-LATENCY-001",
        "definition_version": "1.0.0",
        "reporting_period_start": "2026-10-01",
        "reporting_period_end": "2026-10-31",
        "reporting_timezone": "Africa/Kampala",
        "status": "not_started",
        "value": None,
        "source_refs": [],
        "evidence_refs": [],
        "exclusions": [],
    }
    record.update(overrides)
    return record


def test_missing_metric_is_not_silently_coerced_to_zero():
    result = validate_indicator_measurement(base_record())
    assert result["value"] is None


def test_measured_record_requires_source_and_method():
    record = base_record(status="measured", value=1.42, source_refs=["benchmark://run-01"],
                         calculation_method="p95 of 100 requests")
    assert validate_indicator_measurement(record)["value"] == 1.42

    with pytest.raises(IndicatorMeasurementError, match="source_refs"):
        validate_indicator_measurement(base_record(status="measured", value=1.42))


def test_verified_record_requires_evidence_reviewer_and_timezone():
    record = base_record(
        status="verified",
        value=1.42,
        source_refs=["benchmark://run-01"],
        calculation_method="p95 of 100 requests",
        evidence_refs=["artifact://benchmark-report"],
        reviewer_id="reviewer-01",
        verified_at="2026-10-26T10:00:00+03:00",
    )
    assert validate_indicator_measurement(record)["status"] == "verified"

    record["verified_at"] = "2026-10-26T10:00:00"
    with pytest.raises(IndicatorMeasurementError, match="timezone"):
        validate_indicator_measurement(record)


@pytest.mark.parametrize("bad_value", [-1, True, float("inf"), "2"])
def test_invalid_numeric_measurements_are_rejected(bad_value):
    with pytest.raises(IndicatorMeasurementError):
        validate_indicator_measurement(base_record(value=bad_value))


def test_reporting_period_and_numerator_denominator_are_checked():
    with pytest.raises(IndicatorMeasurementError, match="precede"):
        validate_indicator_measurement(base_record(
            reporting_period_start="2026-10-31", reporting_period_end="2026-10-01"
        ))
    with pytest.raises(IndicatorMeasurementError, match="numerator"):
        validate_indicator_measurement(base_record(numerator=11, denominator=10))


def test_invalid_status_and_malformed_evidence_are_rejected():
    with pytest.raises(IndicatorMeasurementError, match="status"):
        validate_indicator_measurement(base_record(status="done"))
    with pytest.raises(IndicatorMeasurementError, match="evidence_refs"):
        validate_indicator_measurement(base_record(evidence_refs="not-a-list"))
