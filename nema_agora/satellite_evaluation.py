"""Reproducible offline evaluation for NEMA-AGORA spatial-change candidates.

This module evaluates supplied, independently verified reference fixtures only.
It does not fetch satellite imagery, establish legal findings, or claim live
operational detection performance.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Mapping, Sequence

DEFAULT_MIN_AREA_HA = 0.1
EVALUATION_VERSION = "satellite-eval-v1"


class SatelliteEvaluationError(ValueError):
    """Raised when evaluation inputs are incomplete or internally inconsistent."""


def _number(value: Any, field: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SatelliteEvaluationError(f"{field} must be a numeric value.")
    result = float(value)
    if not isfinite(result) or result < minimum:
        raise SatelliteEvaluationError(f"{field} must be finite and >= {minimum}.")
    return result


def evaluate_change_candidates(
    records: Sequence[Mapping[str, Any]],
    *,
    min_area_ha: float = DEFAULT_MIN_AREA_HA,
) -> dict[str, Any]:
    """Compute confusion-matrix metrics on eligible, verified evaluation units.

    Each record must provide a stable `unit_id`, positive/zero `area_ha`,
    boolean `detected`, boolean `reference_change`, boolean
    `independently_verified`, and boolean `usable`. Units at or below the
    area threshold, unverified reference units, and unusable units are excluded
    with explicit counts. Missing or malformed fields are errors, not zeros.
    """
    threshold = _number(min_area_ha, "min_area_ha")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise SatelliteEvaluationError("records must be a sequence of objects.")

    seen: set[str] = set()
    eligible: list[tuple[bool, bool]] = []
    exclusions = {
        "at_or_below_area_threshold": 0,
        "reference_not_independently_verified": 0,
        "unusable_unit": 0,
    }

    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise SatelliteEvaluationError(f"records[{index}] must be an object.")
        unit_id = record.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id.strip():
            raise SatelliteEvaluationError(f"records[{index}].unit_id must be non-empty.")
        unit_id = unit_id.strip()
        if unit_id in seen:
            raise SatelliteEvaluationError(f"duplicate unit_id: {unit_id}")
        seen.add(unit_id)

        area = _number(record.get("area_ha"), f"records[{index}].area_ha")
        for key in ("detected", "reference_change", "independently_verified", "usable"):
            if not isinstance(record.get(key), bool):
                raise SatelliteEvaluationError(f"records[{index}].{key} must be boolean.")

        if area <= threshold:
            exclusions["at_or_below_area_threshold"] += 1
            continue
        if not record["independently_verified"]:
            exclusions["reference_not_independently_verified"] += 1
            continue
        if not record["usable"]:
            exclusions["unusable_unit"] += 1
            continue
        eligible.append((record["detected"], record["reference_change"]))

    tp = sum(detected and reference for detected, reference in eligible)
    fp = sum(detected and not reference for detected, reference in eligible)
    fn = sum((not detected) and reference for detected, reference in eligible)
    tn = sum((not detected) and (not reference) for detected, reference in eligible)

    def ratio(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    precision = ratio(tp, tp + fp)
    recall = ratio(tp, tp + fn)
    f1 = ratio(2 * tp, (2 * tp) + fp + fn)
    false_positive_rate = ratio(fp, fp + tn)

    return {
        "evaluation_version": EVALUATION_VERSION,
        "state": "EVALUATED" if eligible else "NO_ELIGIBLE_UNITS",
        "interpretation": "OFFLINE_FIXTURE_METRICS_NOT_LIVE_PERFORMANCE",
        "area_threshold_ha": threshold,
        "area_rule": "strictly_greater_than_threshold",
        "counts": {
            "input_units": len(records),
            "eligible_units": len(eligible),
            "excluded_units": sum(exclusions.values()),
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "true_negative": tn,
        },
        "exclusions": exclusions,
        "metrics": {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "false_positive_rate": false_positive_rate,
        },
        "limitations": [
            "Metrics apply only to the supplied evaluation units and declared exclusions.",
            "Reference changes must be independently verified and evaluation selection must be documented.",
            "A candidate detection is an advisory signal, not a legal finding or enforcement decision.",
            "Null metrics mean their denominator is zero; they are not zero performance.",
        ],
    }
