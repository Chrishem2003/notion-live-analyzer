"""Conservative Sentinel-2 index calculations on already-aligned in-memory arrays.

This module does not fetch imagery, reproject/resample bands, authenticate an AOI,
or make legal/environmental findings. Inputs must already share a grid and use
consistent reflectance scaling. Missing, non-finite, cloudy and out-of-AOI pixels
are excluded rather than silently replaced with zero.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

import numpy as np

POLICY_VERSION = "sentinel2-index-contract-v1"
# Sentinel-2 Scene Classification Layer classes conservatively excluded.
EXCLUDED_SCL_CLASSES = frozenset({0, 1, 3, 7, 8, 9, 10, 11})


class PixelProcessingError(ValueError):
    """Raised when bands or masks cannot be interpreted safely."""


def _band(name: str, values: Any) -> np.ndarray:
    try:
        arr = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise PixelProcessingError(f"{name} must be a numeric array.") from exc
    if arr.ndim != 2 or arr.size == 0:
        raise PixelProcessingError(f"{name} must be a non-empty 2D array.")
    return arr


def _ratio_index(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    denominator = a + b
    valid = np.isfinite(a) & np.isfinite(b) & np.isfinite(denominator) & (np.abs(denominator) > 1e-12)
    result = np.full(a.shape, np.nan, dtype=np.float64)
    np.divide(a - b, denominator, out=result, where=valid)
    # Small floating-point overshoots can occur around +/-1.
    result[valid] = np.clip(result[valid], -1.0, 1.0)
    return result, valid


def _summary(values: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    selected = values[mask]
    if selected.size == 0:
        return {"valid_pixel_count": 0, "min": None, "p05": None, "median": None, "p95": None, "max": None, "mean": None}
    return {
        "valid_pixel_count": int(selected.size),
        "min": float(np.min(selected)),
        "p05": float(np.percentile(selected, 5)),
        "median": float(np.median(selected)),
        "p95": float(np.percentile(selected, 95)),
        "max": float(np.max(selected)),
        "mean": float(np.mean(selected)),
    }


def process_sentinel2_bands(
    *,
    b03_green: Any,
    b04_red: Any,
    b08_nir: Any,
    scl: Any,
    aoi_mask: Any | None = None,
    max_invalid_fraction_warning: float = 0.8,
) -> dict[str, Any]:
    """Compute McFeeters NDWI and NDVI from aligned reflectance arrays.

    NDWI = (B03 - B08) / (B03 + B08); NDVI = (B08 - B04) / (B08 + B04).
    All arrays must have identical row/column dimensions. SCL classes in the
    conservative exclusion set and any non-finite band values are masked.
    AOI mask, if supplied, is a boolean array where True means inside the AOI.
    """
    if isinstance(max_invalid_fraction_warning, bool) or not isinstance(max_invalid_fraction_warning, (int, float)) or not np.isfinite(max_invalid_fraction_warning) or not 0 <= max_invalid_fraction_warning <= 1:
        raise PixelProcessingError("max_invalid_fraction_warning must be between 0 and 1.")
    green = _band("B03 green", b03_green)
    red = _band("B04 red", b04_red)
    nir = _band("B08 NIR", b08_nir)
    classes = np.asarray(scl)
    if classes.ndim != 2 or classes.size == 0:
        raise PixelProcessingError("SCL must be a non-empty 2D array.")
    if any(a.shape != green.shape for a in (red, nir, classes)):
        raise PixelProcessingError("B03, B04, B08 and SCL must have exactly the same grid shape; resampling is not performed.")
    if not np.issubdtype(classes.dtype, np.integer):
        if not np.issubdtype(classes.dtype, np.number) or not np.all(np.isfinite(classes)) or not np.all(classes == np.floor(classes)):
            raise PixelProcessingError("SCL must contain integer class codes.")
        classes = classes.astype(np.int16)
    inside = np.ones(green.shape, dtype=bool)
    if aoi_mask is not None:
        inside = np.asarray(aoi_mask)
        if inside.shape != green.shape or inside.ndim != 2 or inside.dtype != np.bool_:
            raise PixelProcessingError("aoi_mask must be a boolean array with the same grid shape.")
    base_valid = (
        inside & np.isfinite(green) & np.isfinite(red) & np.isfinite(nir)
        & ~np.isin(classes, list(EXCLUDED_SCL_CLASSES))
    )
    ndvi, ndvi_math_valid = _ratio_index(nir, red)
    ndwi, ndwi_math_valid = _ratio_index(green, nir)
    ndvi_valid = base_valid & ndvi_math_valid
    ndwi_valid = base_valid & ndwi_math_valid
    total_aoi = int(np.count_nonzero(inside))
    valid_fraction_ndvi = float(np.count_nonzero(ndvi_valid) / total_aoi) if total_aoi else 0.0
    valid_fraction_ndwi = float(np.count_nonzero(ndwi_valid) / total_aoi) if total_aoi else 0.0
    report = {
        "policy_version": POLICY_VERSION,
        "state": "PIXEL_INDICES_COMPUTED_WITH_WARNINGS" if (1 - min(valid_fraction_ndvi, valid_fraction_ndwi)) > max_invalid_fraction_warning else "PIXEL_INDICES_COMPUTED_REVIEW_REQUIRED",
        "indices": {
            "NDVI": {"formula": "(B08 - B04) / (B08 + B04)", **_summary(ndvi, ndvi_valid), "valid_pixel_fraction_within_aoi": valid_fraction_ndvi},
            "NDWI_MCFEETERS": {"formula": "(B03 - B08) / (B03 + B08)", **_summary(ndwi, ndwi_valid), "valid_pixel_fraction_within_aoi": valid_fraction_ndwi},
        },
        "quality": {
            "grid_shape_rows_cols": [int(green.shape[0]), int(green.shape[1])],
            "aoi_pixel_count": total_aoi,
            "excluded_scl_classes": sorted(EXCLUDED_SCL_CLASSES),
            "masked_scl_pixel_count": int(np.count_nonzero(inside & np.isin(classes, list(EXCLUDED_SCL_CLASSES)))),
            "nonfinite_band_pixel_count": int(np.count_nonzero(inside & ~(np.isfinite(green) & np.isfinite(red) & np.isfinite(nir)))),
            "zero_or_invalid_denominator_ndvi_count": int(np.count_nonzero(inside & np.isfinite(nir) & np.isfinite(red) & (np.abs(nir + red) <= 1e-12))),
            "zero_or_invalid_denominator_ndwi_count": int(np.count_nonzero(inside & np.isfinite(green) & np.isfinite(nir) & (np.abs(green + nir) <= 1e-12))),
            "invalid_fraction_warning_threshold": float(max_invalid_fraction_warning),
            "reflectance_scale_declared_by_caller": True,
            "grid_alignment_verified_by_processor": False,
        },
        "limitations": [
            "Inputs must be independently verified to be co-registered, same-resolution arrays with consistent reflectance scaling.",
            "SCL masking is conservative but does not replace visual QA or AOI-specific quality review.",
            "NDWI_MCFEETERS is a green-NIR water index; it is not a legal wetland determination.",
            "No imagery was downloaded, georeferencing was not checked, and no change detection or enforcement decision was performed.",
        ],
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    report["report_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return report
