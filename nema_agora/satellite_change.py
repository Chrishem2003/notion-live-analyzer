"""Reproducible two-date index comparison for already-validated raster reports.

This layer accepts reports produced by the pixel-index processor, plus explicit
acquisition/grid metadata supplied by a trusted ingestion adapter. It does not
open files, discover scenes, infer grid equivalence, or assert environmental
change. Caller must supply per-pixel index arrays for both dates and a shared
valid-data mask after validating the source grids and masks.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

import numpy as np


class ChangeComparisonError(ValueError):
    """Raised when two-date comparison prerequisites are not met."""


def _date(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise ChangeComparisonError(f"{label} must be an ISO-8601 datetime with timezone.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ChangeComparisonError(f"{label} must be an ISO-8601 datetime with timezone.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ChangeComparisonError(f"{label} must include a timezone.")
    return parsed


def _signature(meta: dict[str, Any], label: str) -> tuple[Any, ...]:
    required = ("crs", "width", "height", "transform", "grid_id", "reflectance_scale_id", "processing_baseline")
    missing = [key for key in required if meta.get(key) in (None, "", [])]
    if missing:
        raise ChangeComparisonError(f"{label} metadata missing: {', '.join(missing)}.")
    transform = meta["transform"]
    if not isinstance(transform, (list, tuple)) or len(transform) != 6:
        raise ChangeComparisonError(f"{label} transform must contain six affine coefficients.")
    try:
        transform_tuple = tuple(float(v) for v in transform)
        width, height = int(meta["width"]), int(meta["height"])
    except (TypeError, ValueError, OverflowError) as exc:
        raise ChangeComparisonError(f"{label} grid metadata is invalid.") from exc
    if width <= 0 or height <= 0 or any(not np.isfinite(v) for v in transform_tuple):
        raise ChangeComparisonError(f"{label} grid metadata is invalid.")
    return (
        str(meta["crs"]), width, height, transform_tuple, str(meta["grid_id"]),
        str(meta["reflectance_scale_id"]), str(meta["processing_baseline"]),
    )


def compare_two_dates(
    *,
    earlier: dict[str, Any],
    later: dict[str, Any],
    earlier_ndvi: Any,
    later_ndvi: Any,
    earlier_ndwi: Any,
    later_ndwi: Any,
    shared_valid_mask: Any,
    comparison_domain_mask: Any | None = None,
    ndvi_change_threshold: float = 0.15,
    ndwi_change_threshold: float = 0.15,
    minimum_valid_fraction: float = 0.7,
) -> dict[str, Any]:
    """Compare paired index arrays only after explicit metadata compatibility checks."""
    if not isinstance(earlier, dict) or not isinstance(later, dict):
        raise ChangeComparisonError("Earlier and later metadata must be objects.")
    earlier_date = _date(earlier.get("acquired_at"), "earlier.acquired_at")
    later_date = _date(later.get("acquired_at"), "later.acquired_at")
    if later_date <= earlier_date:
        raise ChangeComparisonError("Later acquisition must be strictly after earlier acquisition.")
    sig_a = _signature(earlier, "earlier")
    sig_b = _signature(later, "later")
    if sig_a != sig_b:
        raise ChangeComparisonError("Grid, CRS, transform, scale identity or processing baseline differs; comparison is blocked.")
    for name, value in (("ndvi_change_threshold", ndvi_change_threshold), ("ndwi_change_threshold", ndwi_change_threshold)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or not 0 < value <= 2:
            raise ChangeComparisonError(f"{name} must be finite and in (0, 2].")
    if isinstance(minimum_valid_fraction, bool) or not isinstance(minimum_valid_fraction, (int, float)) or not np.isfinite(minimum_valid_fraction) or not 0 < minimum_valid_fraction <= 1:
        raise ChangeComparisonError("minimum_valid_fraction must be in (0, 1].")
    try:
        a_ndvi, b_ndvi = np.asarray(earlier_ndvi, dtype=float), np.asarray(later_ndvi, dtype=float)
        a_ndwi, b_ndwi = np.asarray(earlier_ndwi, dtype=float), np.asarray(later_ndwi, dtype=float)
        valid = np.asarray(shared_valid_mask)
    except (TypeError, ValueError) as exc:
        raise ChangeComparisonError("Index arrays and shared mask have invalid types.") from exc
    shape = (sig_a[2], sig_a[1])
    if any(a.shape != shape for a in (a_ndvi, b_ndvi, a_ndwi, b_ndwi, valid)):
        raise ChangeComparisonError("All index arrays and shared mask must match the declared grid shape.")
    if valid.dtype != np.bool_:
        raise ChangeComparisonError("shared_valid_mask must be boolean.")
    if comparison_domain_mask is None:
        domain = np.ones(shape, dtype=bool)
    else:
        domain = np.asarray(comparison_domain_mask)
        if domain.shape != shape or domain.dtype != np.bool_:
            raise ChangeComparisonError("comparison_domain_mask must be boolean and match the declared grid.")
    finite = np.isfinite(a_ndvi) & np.isfinite(b_ndvi) & np.isfinite(a_ndwi) & np.isfinite(b_ndwi)
    valid = valid & domain & finite
    total = int(np.count_nonzero(domain))
    count = int(np.count_nonzero(valid))
    fraction = count / total if total else 0.0
    if fraction < minimum_valid_fraction:
        raise ChangeComparisonError(
            f"Shared valid-pixel fraction {fraction:.4f} is below required {minimum_valid_fraction:.4f}; comparison blocked."
        )
    delta_ndvi = b_ndvi - a_ndvi
    delta_ndwi = b_ndwi - a_ndwi
    def stats(values: np.ndarray) -> dict[str, Any]:
        selected = values[valid]
        return {
            "median_delta": float(np.median(selected)),
            "mean_delta": float(np.mean(selected)),
            "p05_delta": float(np.percentile(selected, 5)),
            "p95_delta": float(np.percentile(selected, 95)),
            "absolute_change_threshold": None,
            "pixels_above_positive_threshold": None,
            "pixels_below_negative_threshold": None,
        }
    ndvi_stats = stats(delta_ndvi)
    ndwi_stats = stats(delta_ndwi)
    ndvi_stats.update({
        "absolute_change_threshold": float(ndvi_change_threshold),
        "pixels_above_positive_threshold": int(np.count_nonzero(valid & (delta_ndvi >= ndvi_change_threshold))),
        "pixels_below_negative_threshold": int(np.count_nonzero(valid & (delta_ndvi <= -ndvi_change_threshold))),
    })
    ndwi_stats.update({
        "absolute_change_threshold": float(ndwi_change_threshold),
        "pixels_above_positive_threshold": int(np.count_nonzero(valid & (delta_ndwi >= ndwi_change_threshold))),
        "pixels_below_negative_threshold": int(np.count_nonzero(valid & (delta_ndwi <= -ndwi_change_threshold))),
    })
    report = {
        "state": "TWO_DATE_SCREENING_REVIEW_REQUIRED",
        "policy_version": "two-date-index-comparison-v1",
        "earlier": {"acquired_at": earlier_date.isoformat(), "source_sha256": earlier.get("source_sha256")},
        "later": {"acquired_at": later_date.isoformat(), "source_sha256": later.get("source_sha256")},
        "compatibility": {
            "same_crs_grid_transform_and_dimensions": True,
            "same_grid_id": True,
            "same_reflectance_scale_id": True,
            "same_processing_baseline": True,
            "shared_valid_pixel_count": count,
            "total_comparison_domain_pixels": total,
            "shared_valid_pixel_fraction": fraction,
            "coverage_denominator": "comparison domain (AOI when supplied)",
            "minimum_valid_pixel_fraction": float(minimum_valid_fraction),
        },
        "indices": {"NDVI_delta": ndvi_stats, "NDWI_MCFEETERS_delta": ndwi_stats},
        "limitations": [
            "Grid and processing metadata equality is asserted by identifiers supplied to this function; source authenticity and grid registration are not independently proven here.",
            "Threshold exceedance is a screening flag, not proof of environmental change, causation, wetland loss or a legal violation.",
            "Seasonality, phenology, atmosphere, topography, residual clouds, sensor artefacts and reference observations must be assessed independently.",
            "Pixel counts are not converted to area because this contract does not independently validate projected pixel area or ground-area distortion.",
        ],
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    report["report_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return report
