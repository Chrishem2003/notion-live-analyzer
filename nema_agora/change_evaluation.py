"""Evaluation metrics for binary environmental-change detections.

Consumes counts produced from a predeclared, independently reviewed reference set.
It does not ingest imagery or decide legal/environmental findings. Metrics with a
zero denominator are returned as None rather than fabricated as zero.
"""
from __future__ import annotations

import math
from typing import Any, Mapping


class ChangeEvaluationError(ValueError):
    """Raised for invalid confusion-matrix counts or confidence parameters."""


def _count(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ChangeEvaluationError(f"{field} must be a non-negative integer.")
    return value


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _wilson_interval(successes: int, trials: int, z: float) -> tuple[float, float] | None:
    if trials == 0:
        return None
    p = successes / trials
    z2 = z * z
    denom = 1 + z2 / trials
    centre = (p + z2 / (2 * trials)) / denom
    half = z * math.sqrt((p * (1 - p) / trials) + z2 / (4 * trials * trials)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def evaluate_change_detections(
    counts: Mapping[str, Any],
    *,
    confidence_z: float = 1.959963984540054,
    evaluation_set_id: str,
    threshold_hectares: float,
    processing_version: str,
) -> dict[str, Any]:
    """Compute recall/precision and Wilson confidence intervals.

    Required counts are TP, FP, FN, TN from a declared reference evaluation set.
    TP/FN refer to independently confirmed eligible changes meeting the area
    threshold; FP/TN refer to reference-reviewed non-change candidates/units.
    This function cannot establish that labels are truly independent; callers must
    retain the protocol and source evidence separately.
    """
    if not isinstance(counts, Mapping):
        raise ChangeEvaluationError("counts must be an object.")
    if not isinstance(evaluation_set_id, str) or not evaluation_set_id.strip():
        raise ChangeEvaluationError("evaluation_set_id is required.")
    if not isinstance(processing_version, str) or not processing_version.strip():
        raise ChangeEvaluationError("processing_version is required.")
    if isinstance(threshold_hectares, bool) or not isinstance(threshold_hectares, (int, float)) or not math.isfinite(threshold_hectares) or threshold_hectares <= 0:
        raise ChangeEvaluationError("threshold_hectares must be a finite positive number.")
    if isinstance(confidence_z, bool) or not isinstance(confidence_z, (int, float)) or not math.isfinite(confidence_z) or confidence_z <= 0:
        raise ChangeEvaluationError("confidence_z must be a finite positive number.")

    tp = _count(counts.get("true_positive"), "true_positive")
    fp = _count(counts.get("false_positive"), "false_positive")
    fn = _count(counts.get("false_negative"), "false_negative")
    tn = _count(counts.get("true_negative"), "true_negative")
    positives = tp + fn
    predicted_positives = tp + fp
    negatives = fp + tn
    total = tp + fp + fn + tn
    if total == 0:
        raise ChangeEvaluationError("At least one reference-reviewed unit is required.")

    recall = _ratio(tp, positives)
    precision = _ratio(tp, predicted_positives)
    specificity = _ratio(tn, negatives)
    f1 = None if precision is None or recall is None or precision + recall == 0 else 2 * precision * recall / (precision + recall)
    recall_ci = _wilson_interval(tp, positives, float(confidence_z))
    precision_ci = _wilson_interval(tp, predicted_positives, float(confidence_z))
    specificity_ci = _wilson_interval(tn, negatives, float(confidence_z))

    def interval(value: tuple[float, float] | None) -> dict[str, float] | None:
        if value is None:
            return None
        return {"lower": value[0], "upper": value[1]}

    return {
        "evaluation_set_id": evaluation_set_id.strip(),
        "processing_version": processing_version.strip(),
        "threshold_hectares": float(threshold_hectares),
        "confidence_level_approx": 0.95 if math.isclose(float(confidence_z), 1.959963984540054, rel_tol=1e-6) else None,
        "counts": {
            "true_positive": tp, "false_positive": fp,
            "false_negative": fn, "true_negative": tn,
            "reference_units": total,
            "confirmed_change_units": positives,
            "reference_non_change_units": negatives,
        },
        "metrics": {
            "recall": recall,
            "recall_wilson_interval": interval(recall_ci),
            "precision": precision,
            "precision_wilson_interval": interval(precision_ci),
            "specificity": specificity,
            "specificity_wilson_interval": interval(specificity_ci),
            "f1": f1,
            "false_positive_rate": _ratio(fp, negatives),
        },
        "limitations": [
            "Metrics apply only to the declared evaluation set and processing version.",
            "Confidence intervals do not correct biased or non-independent reference sampling.",
            "A satellite detection is a candidate for review, not a legal finding.",
            "A zero denominator produces null, not a zero performance score.",
        ],
    }
