"""Tests for the offline NEMA-AGORA satellite evaluation harness."""
import pytest

from nema_agora.satellite_evaluation import (
    SatelliteEvaluationError,
    evaluate_change_candidates,
)


def row(unit_id, detected, reference_change, **overrides):
    record = {
        "unit_id": unit_id,
        "area_ha": 0.2,
        "detected": detected,
        "reference_change": reference_change,
        "independently_verified": True,
        "usable": True,
    }
    record.update(overrides)
    return record


def test_confusion_matrix_and_metrics_are_calculated_from_verified_units():
    result = evaluate_change_candidates([
        row("tp", True, True),
        row("fp", True, False),
        row("fn", False, True),
        row("tn", False, False),
    ])
    assert result["state"] == "EVALUATED"
    assert result["counts"]["eligible_units"] == 4
    assert result["counts"]["true_positive"] == 1
    assert result["counts"]["false_positive"] == 1
    assert result["counts"]["false_negative"] == 1
    assert result["counts"]["true_negative"] == 1
    assert result["metrics"]["precision"] == pytest.approx(0.5)
    assert result["metrics"]["recall"] == pytest.approx(0.5)
    assert result["metrics"]["f1_score"] == pytest.approx(0.5)
    assert result["metrics"]["false_positive_rate"] == pytest.approx(0.5)
    assert result["interpretation"] == "OFFLINE_FIXTURE_METRICS_NOT_LIVE_PERFORMANCE"


def test_area_threshold_is_strict_and_exclusions_are_reported():
    result = evaluate_change_candidates([
        row("exact-threshold", True, True, area_ha=0.1),
        row("below-threshold", True, True, area_ha=0.05),
        row("unverified", True, True, independently_verified=False),
        row("unusable", False, True, usable=False),
        row("eligible", True, True, area_ha=0.11),
    ])
    assert result["counts"]["eligible_units"] == 1
    assert result["counts"]["excluded_units"] == 4
    assert result["exclusions"] == {
        "at_or_below_area_threshold": 2,
        "reference_not_independently_verified": 1,
        "unusable_unit": 1,
    }


def test_empty_denominators_are_null_not_zero():
    result = evaluate_change_candidates([row("only-negative", False, False)])
    assert result["metrics"]["precision"] is None
    assert result["metrics"]["recall"] is None
    assert result["metrics"]["f1_score"] == 0.0
    assert result["metrics"]["false_positive_rate"] == 0.0


def test_no_eligible_units_is_not_reported_as_a_success():
    result = evaluate_change_candidates([row("excluded", True, True, area_ha=0.1)])
    assert result["state"] == "NO_ELIGIBLE_UNITS"
    assert result["counts"]["eligible_units"] == 0


def test_duplicate_units_are_rejected():
    with pytest.raises(SatelliteEvaluationError, match="duplicate"):
        evaluate_change_candidates([row("same", True, True), row("same", False, False)])


@pytest.mark.parametrize("bad_area", [-0.1, float("inf"), True, "0.2"])
def test_invalid_area_is_rejected(bad_area):
    with pytest.raises(SatelliteEvaluationError):
        evaluate_change_candidates([row("bad", True, True, area_ha=bad_area)])


def test_missing_or_non_boolean_truth_fields_are_rejected():
    bad = row("bad", True, True)
    bad["reference_change"] = None
    with pytest.raises(SatelliteEvaluationError, match="reference_change"):
        evaluate_change_candidates([bad])
