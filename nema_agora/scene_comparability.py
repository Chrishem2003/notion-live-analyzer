"""Pre-analysis comparability gates for paired environmental raster scenes.

This module distinguishes hard incompatibilities from review warnings. It does not
prove scientific comparability, sensor equivalence, source authenticity, or legality.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def assess_scene_comparability(
    baseline: Mapping[str, Any],
    comparison: Mapping[str, Any],
    *,
    max_interval_days: int = 180,
    max_day_of_year_gap: int = 45,
    min_valid_fraction: float = 0.70,
) -> dict[str, Any]:
    """Return deterministic blocking findings and review warnings for a scene pair."""
    blocking: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    if not isinstance(baseline, Mapping) or not isinstance(comparison, Mapping):
        return {"state": "CONTROL_REQUIRED", "blocking_findings": [{"code": "SCENES_MUST_BE_OBJECTS"}], "warnings": []}
    if isinstance(max_interval_days, bool) or not isinstance(max_interval_days, int) or max_interval_days < 1:
        blocking.append({"code": "INVALID_MAX_INTERVAL_DAYS"})
    if isinstance(max_day_of_year_gap, bool) or not isinstance(max_day_of_year_gap, int) or not 0 <= max_day_of_year_gap <= 183:
        blocking.append({"code": "INVALID_MAX_DAY_OF_YEAR_GAP"})
    if isinstance(min_valid_fraction, bool) or not isinstance(min_valid_fraction, (int, float)) or not 0 < min_valid_fraction <= 1:
        blocking.append({"code": "INVALID_MIN_VALID_FRACTION"})
    for field in ("scene_id", "acquired_at", "aoi_id", "grid_id", "crs", "valid_mask", "domain_mask", "ingestion"):
        if field not in baseline:
            blocking.append({"code": f"BASELINE_MISSING_{field.upper()}"})
        if field not in comparison:
            blocking.append({"code": f"COMPARISON_MISSING_{field.upper()}"})
    if blocking:
        return {"state": "CONTROL_REQUIRED", "blocking_findings": blocking, "warnings": warnings}

    b_time, c_time = _timestamp(baseline["acquired_at"]), _timestamp(comparison["acquired_at"])
    if b_time is None:
        blocking.append({"code": "BASELINE_INVALID_ACQUISITION_TIME"})
    if c_time is None:
        blocking.append({"code": "COMPARISON_INVALID_ACQUISITION_TIME"})
    if b_time is not None and c_time is not None:
        if b_time >= c_time:
            blocking.append({"code": "BASELINE_MUST_PRECEDE_COMPARISON"})
        else:
            interval = (c_time - b_time).total_seconds() / 86400
            if interval > max_interval_days:
                warnings.append({"code": "SCENE_INTERVAL_EXCEEDS_REVIEW_THRESHOLD", "detail": f"{interval:.2f} days"})
            # Circular day-of-year distance avoids treating Dec 31 and Jan 1 as far apart.
            b_day, c_day = b_time.timetuple().tm_yday, c_time.timetuple().tm_yday
            doy_gap = min(abs(c_day - b_day), 366 - abs(c_day - b_day))
            if doy_gap > max_day_of_year_gap:
                warnings.append({"code": "SEASONAL_WINDOW_DIFFERENCE_REQUIRES_REVIEW", "detail": f"{doy_gap} day-of-year days"})
    for field, code in (("aoi_id", "AOI_ID_MISMATCH"), ("grid_id", "GRID_ID_MISMATCH"), ("crs", "CRS_MISMATCH")):
        if baseline[field] != comparison[field]:
            blocking.append({"code": code})
    if baseline["domain_mask"] != comparison["domain_mask"]:
        blocking.append({"code": "AOI_DOMAIN_MASK_MISMATCH"})

    for name, scene in (("BASELINE", baseline), ("COMPARISON", comparison)):
        ingestion = scene.get("ingestion")
        if not isinstance(ingestion, Mapping):
            blocking.append({"code": f"{name}_INGESTION_METADATA_REQUIRED"})
            continue
        scale = ingestion.get("reflectance_scale")
        offset = ingestion.get("reflectance_offset", 0.0)
        if isinstance(scale, bool) or not isinstance(scale, (int, float)) or scale <= 0:
            blocking.append({"code": f"{name}_INVALID_REFLECTANCE_SCALE"})
        if isinstance(offset, bool) or not isinstance(offset, (int, float)):
            blocking.append({"code": f"{name}_INVALID_REFLECTANCE_OFFSET"})
        if ingestion.get("band_mapping_confirmed_by_uploader") is not True:
            blocking.append({"code": f"{name}_BAND_MAPPING_NOT_CONFIRMED"})
        if ingestion.get("cloud_shadow_mask_applied_by_uploader") is not True:
            blocking.append({"code": f"{name}_CLOUD_MASK_NOT_CONFIRMED")
        fraction = ingestion.get("aoi_valid_pixel_fraction")
        if fraction is None:
            fraction = scene.get("valid_fraction")
        if isinstance(fraction, bool) or not isinstance(fraction, (int, float)) or not 0 <= fraction <= 1:
            blocking.append({"code": f"{name}_INVALID_VALID_PIXEL_FRACTION"})
        elif fraction < min_valid_fraction:
            blocking.append({"code": f"{name}_VALID_PIXEL_FRACTION_BELOW_THRESHOLD"})

    bi, ci = baseline.get("ingestion"), comparison.get("ingestion")
    if isinstance(bi, Mapping) and isinstance(ci, Mapping):
        if bi.get("reflectance_scale") != ci.get("reflectance_scale") or bi.get("reflectance_offset", 0.0) != ci.get("reflectance_offset", 0.0):
            blocking.append({"code": "REFLECTANCE_SCALING_MISMATCH"})
        if bi.get("band_mapping") != ci.get("band_mapping"):
            blocking.append({"code": "BAND_MAPPING_MISMATCH"})
        if bi.get("raster_driver") != ci.get("raster_driver"):
            warnings.append({"code": "SOURCE_FORMAT_DIFFERENCE_REQUIRES_REVIEW"})

    return {
        "policy_version": "scene-comparability-v1",
        "state": "CONTROL_REQUIRED" if blocking else ("REVIEW_WARNINGS" if warnings else "COMPARABILITY_CHECKS_PASSED"),
        "blocking_findings": blocking,
        "warnings": warnings,
        "review_boundary": "Passing checks do not establish scientific comparability; a qualified reviewer must assess sensor/product level, cloud-mask provenance, seasonality, registration, and local conditions.",
        "thresholds": {
            "max_interval_days": max_interval_days,
            "max_day_of_year_gap": max_day_of_year_gap,
            "min_valid_fraction": min_valid_fraction,
            "thresholds_are_screening_defaults": True,
        },
    }
