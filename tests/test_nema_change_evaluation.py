"""Regression tests for environmental change evaluation metrics."""
import pytest

from nema_agora.change_evaluation import (
    ChangeEvaluationError,
    evaluate_change_detections,
)


def _evaluate(counts, **overrides):
    kwargs = {
        "evaluation_set_id": "uganda-wetland-reference-v1",
        "threshold_hectares": 0.1,
        "processing_version": "sentinel-pipeline-1.2.0",
    }
    kwargs.update(overrides)
    return evaluate_change_detections(counts, **kwargs)


def test_computes_recall_precision_specificity_and_f1():
    result = _evaluate({
        "true_positive": 8,
        "false_positive": 2,
        "false_negative": 2,
        "true_negative": 18,
    })
    assert result["metrics"]["recall"] == pytest.approx(0.8)
    assert result["metrics"]["precision"] == pytest.approx(0.8)
    assert result["metrics"]["specificity"] == pytest.approx(0.9)
    assert result["metrics"]["f1"] == pytest.approx(0.8)
    assert result["metrics"]["recall_wilson_interval"]["lower"] < 0.8
    assert result["metrics"]["recall_wilson_interval"]["upper"] > 0.8
    assert result["counts"]["reference_units"] == 30


def test_zero_denominator_is_null_not_zero():
    result = _evaluate({
        "true_positive": 0,
        "false_positive": 0,
        "false_negative": 0,
        "true_negative": 7,
    })
    assert result["metrics"]["recall"] is None
    assert result["metrics"]["precision"] is None
    assert result["metrics"]["specificity"] == pytest.approx(1.0)
    assert result["metrics"]["recall_wilson_interval"] is None
    assert result["metrics"]["precision_wilson_interval"] is None


def test_all_counts_zero_is_rejected():
    with pytest.raises(ChangeEvaluationError, match="At least one"):
        _evaluate({"true_positive": 0, "false_positive": 0, "false_negative": 0, "true_negative": 0})


@pytest.mark.parametrize("bad", [-1, 1.5, True, "3", None])
def test_invalid_confusion_counts_are_rejected(bad):
    with pytest.raises(ChangeEvaluationError, match="true_positive"):
        _evaluate({"true_positive": bad, "false_positive": 0, "false_negative": 0, "true_negative": 1})


@pytest.mark.parametrize("threshold", [0, -0.1, float("nan"), float("inf"), True])
def test_invalid_area_threshold_is_rejected(threshold):
    with pytest.raises(ChangeEvaluationError, match="threshold_hectares"):
        _evaluate({"true_positive": 1, "false_positive": 0, "false_negative": 0, "true_negative": 1}, threshold_hectares=threshold)


def test_empty_metadata_is_rejected():
    with pytest.raises(ChangeEvaluationError, match="evaluation_set_id"):
        _evaluate({"true_positive": 1, "false_positive": 0, "false_negative": 0, "true_negative": 1}, evaluation_set_id=" ")


def test_confidence_intervals_are_bounded():
    result = _evaluate({
        "true_positive": 100,
        "false_positive": 0,
        "false_negative": 0,
        "true_negative": 100,
    })
    for metric in ("recall", "precision", "specificity"):
        ci = result["metrics"][f"{metric}_wilson_interval"]
        assert 0 <= ci["lower"] <= ci["upper"] <= 1
