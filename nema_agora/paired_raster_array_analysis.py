"""Deterministic pixel-array NDVI/NDWI analysis for paired raster scenes.

Inputs are already-decoded, normalized reflectance arrays (0..1) plus explicit
valid-pixel masks. This module performs numeric analysis; it does not read GeoTIFFs,
fetch satellite data, reproject/resample grids, or verify provider authenticity.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

POLICY_VERSION = "paired-array-analysis-v1"
MAX_PIXELS = 250_000
_REQUIRED_BANDS = ("B03", "B04", "B08")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None


def _matrix(value: Any, name: str) -> tuple[int, int]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError(f"{name}_MUST_BE_NONEMPTY_2D_ARRAY")
    width: int | None = None
    for row in value:
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)) or not row:
            raise ValueError(f"{name}_ROW_MUST_BE_NONEMPTY")
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise ValueError(f"{name}_ROWS_MUST_HAVE_EQUAL_WIDTH")
    return len(value), int(width)


def _valid_mask(mask: Any, shape: tuple[int, int], name: str) -> list[list[bool]]:
    if _matrix(mask, name) != shape:
        raise ValueError(f"{name}_SHAPE_MISMATCH")
    result: list[list[bool]] = []
    for row in mask:
        parsed = []
        for value in row:
            if not isinstance(value, bool):
                raise ValueError(f"{name}_VALUES_MUST_BE_BOOLEAN")
            parsed.append(value)
        result.append(parsed)
    return result


def _scene(scene: Mapping[str, Any], name: str) -> dict[str, Any]:
    if not isinstance(scene, Mapping):
        raise ValueError(f"{name}_MUST_BE_OBJECT")
    for field in ("scene_id", "acquired_at", "aoi_id", "grid_id", "crs", "bands", "valid_mask", "cloud_mask_applied"):
        if field not in scene:
            raise ValueError(f"{name}_MISSING_{field.upper()}")
    for field in ("scene_id", "aoi_id", "grid_id"):
        if not isinstance(scene[field], str) or not scene[field].strip():
            raise ValueError(f"{name}_INVALID_{field.upper()}")
    if scene["crs"] != "EPSG:4326":
        raise ValueError(f"{name}_UNSUPPORTED_CRS")
    if scene["cloud_mask_applied"] is not True:
        raise ValueError(f"{name}_CLOUD_MASK_REQUIRED")
    acquired = _timestamp(scene["acquired_at"])
    if acquired is None:
        raise ValueError(f"{name}_INVALID_ACQUISITION_TIME")
    bands = scene["bands"]
    if not isinstance(bands, Mapping) or not all(key in bands for key in _REQUIRED_BANDS):
        raise ValueError(f"{name}_REQUIRED_BANDS_MISSING")
    shape = _matrix(bands["B03"], f"{name}_B03")
    if shape[0] * shape[1] > MAX_PIXELS:
        raise ValueError(f"{name}_PIXEL_LIMIT_EXCEEDED")
    for band in _REQUIRED_BANDS:
        if _matrix(bands[band], f"{name}_{band}") != shape:
            raise ValueError(f"{name}_BAND_SHAPE_MISMATCH")
    clean_bands: dict[str, list[list[float]]] = {}
    for band in _REQUIRED_BANDS:
        rows = []
        for row in bands[band]:
            vals = []
            for value in row:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or not 0 <= float(value) <= 1:
                    raise ValueError(f"{name}_INVALID_{band}_REFLECTANCE")
                vals.append(float(value))
            rows.append(vals)
        clean_bands[band] = rows
    mask = _valid_mask(scene["valid_mask"], shape, f"{name}_VALID_MASK")
    valid_count = sum(sum(1 for v in row if v) for row in mask)
    fraction = valid_count / (shape[0] * shape[1])
    if valid_count == 0:
        raise ValueError(f"{name}_NO_VALID_PIXELS")
    return {
        "scene_id": scene["scene_id"].strip(),
        "acquired_at": acquired,
        "aoi_id": scene["aoi_id"].strip(),
        "grid_id": scene["grid_id"].strip(),
        "crs": scene["crs"],
        "bands": clean_bands,
        "valid_mask": mask,
        "shape": shape,
        "valid_fraction": fraction,
        "source_fingerprint": _digest({
            "scene_id": scene["scene_id"], "acquired_at": scene["acquired_at"],
            "aoi_id": scene["aoi_id"], "grid_id": scene["grid_id"], "crs": scene["crs"],
            "bands": clean_bands, "valid_mask": mask, "cloud_mask_applied": True,
        }),
    }


def analyze_paired_raster_arrays(
    *,
    baseline_scene: Mapping[str, Any],
    comparison_scene: Mapping[str, Any],
    min_valid_fraction: float = 0.70,
    min_abs_ndvi_delta: float = 0.15,
    min_abs_ndwi_delta: float = 0.15,
) -> dict[str, Any]:
    """Calculate pixelwise NDVI/NDWI deltas only for valid, aligned scene arrays."""
    findings: list[str] = []
    if isinstance(min_valid_fraction, bool) or not isinstance(min_valid_fraction, (int, float)) or not math.isfinite(float(min_valid_fraction)) or not 0 < float(min_valid_fraction) <= 1:
        findings.append("INVALID_MIN_VALID_FRACTION")
    for name, value in (("MIN_ABS_NDVI_DELTA", min_abs_ndvi_delta), ("MIN_ABS_NDWI_DELTA", min_abs_ndwi_delta)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or not 0 <= float(value) <= 2:
            findings.append(f"INVALID_{name}")
    try:
        baseline = _scene(baseline_scene, "BASELINE")
        comparison = _scene(comparison_scene, "COMPARISON")
    except (ValueError, TypeError) as exc:
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED", "findings": [{"code": str(exc)}]}
    if baseline["aoi_id"] != comparison["aoi_id"]:
        findings.append("AOI_ID_MISMATCH")
    if baseline["grid_id"] != comparison["grid_id"]:
        findings.append("GRID_ID_MISMATCH")
    if baseline["crs"] != comparison["crs"]:
        findings.append("CRS_MISMATCH")
    if baseline["shape"] != comparison["shape"]:
        findings.append("RASTER_SHAPE_MISMATCH")
    if baseline["acquired_at"] >= comparison["acquired_at"]:
        findings.append("BASELINE_MUST_PRECEDE_COMPARISON")
    if baseline["valid_fraction"] < float(min_valid_fraction):
        findings.append("BASELINE_VALID_FRACTION_BELOW_THRESHOLD")
    if comparison["valid_fraction"] < float(min_valid_fraction):
        findings.append("COMPARISON_VALID_FRACTION_BELOW_THRESHOLD")
    if findings:
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED", "findings": [{"code": code} for code in findings]}

    valid_pixels = 0
    index_values: dict[str, list[list[float | None]]] = {
        "baseline_ndvi": [], "comparison_ndvi": [], "ndvi_delta": [],
        "baseline_ndwi_mcfeeters": [], "comparison_ndwi_mcfeeters": [], "ndwi_delta": [],
        "candidate_change_mask": [],
    }
    deltas: dict[str, list[float]] = {"NDVI": [], "NDWI_MCFEETERS": []}
    for row_idx in range(baseline["shape"][0]):
        rows: dict[str, list[Any]] = {key: [] for key in index_values}
        for col_idx in range(baseline["shape"][1]):
            valid = baseline["valid_mask"][row_idx][col_idx] and comparison["valid_mask"][row_idx][col_idx]
            if not valid:
                for key in rows:
                    rows[key].append(None)
                continue
            b_bands, c_bands = baseline["bands"], comparison["bands"]
            def ndvi(b: Mapping[str, Any]) -> float | None:
                denom = b["B08"][row_idx][col_idx] + b["B04"][row_idx][col_idx]
                return None if denom == 0 else (b["B08"][row_idx][col_idx] - b["B04"][row_idx][col_idx]) / denom
            def ndwi(b: Mapping[str, Any]) -> float | None:
                denom = b["B03"][row_idx][col_idx] + b["B08"][row_idx][col_idx]
                return None if denom == 0 else (b["B03"][row_idx][col_idx] - b["B08"][row_idx][col_idx]) / denom
            b_ndvi, c_ndvi = ndvi(b_bands), ndvi(c_bands)
            b_ndwi, c_ndwi = ndwi(b_bands), ndwi(c_bands)
            if None in (b_ndvi, c_ndvi, b_ndwi, c_ndwi):
                for key in rows:
                    rows[key].append(None)
                continue
            d_ndvi, d_ndwi = c_ndvi - b_ndvi, c_ndwi - b_ndwi
            valid_pixels += 1
            deltas["NDVI"].append(d_ndvi)
            deltas["NDWI_MCFEETERS"].append(d_ndwi)
            for key, value in (
                ("baseline_ndvi", b_ndvi), ("comparison_ndvi", c_ndvi), ("ndvi_delta", d_ndvi),
                ("baseline_ndwi_mcfeeters", b_ndwi), ("comparison_ndwi_mcfeeters", c_ndwi),
                ("ndwi_delta", d_ndwi),
                ("candidate_change_mask", abs(d_ndvi) >= float(min_abs_ndvi_delta) or abs(d_ndwi) >= float(min_abs_ndwi_delta)),
            ):
                rows[key].append(round(value, 8) if isinstance(value, float) else value)
        for key in rows:
            index_values[key].append(rows[key])
    if valid_pixels == 0:
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED", "findings": [{"code": "NO_COMPARABLE_VALID_PIXELS"}]}
    if valid_pixels / (baseline["shape"][0] * baseline["shape"][1]) < float(min_valid_fraction):
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED", "findings": [{"code": "JOINT_VALID_FRACTION_BELOW_THRESHOLD"}]}

    def stats(name: str, values: list[float]) -> dict[str, float]:
        return {
            "mean": round(sum(values) / len(values), 8),
            "min": round(min(values), 8),
            "max": round(max(values), 8),
            "mean_absolute": round(sum(abs(v) for v in values) / len(values), 8),
            "threshold_hit_pixels": sum(abs(v) >= (float(min_abs_ndvi_delta) if name == "NDVI" else float(min_abs_ndwi_delta)) for v in values),
        }
    summaries = {name: stats(name, values) for name, values in deltas.items()}
    total_pixels = baseline["shape"][0] * baseline["shape"][1]
    payload = {
        "policy_version": POLICY_VERSION,
        "state": "PIXEL_ANALYSIS_COMPLETE",
        "baseline": {"scene_id": baseline["scene_id"], "acquired_at": baseline_scene["acquired_at"], "source_fingerprint": baseline["source_fingerprint"], "valid_fraction": round(baseline["valid_fraction"], 8)},
        "comparison": {"scene_id": comparison["scene_id"], "acquired_at": comparison_scene["acquired_at"], "source_fingerprint": comparison["source_fingerprint"], "valid_fraction": round(comparison["valid_fraction"], 8)},
        "grid": {"aoi_id": baseline["aoi_id"], "grid_id": baseline["grid_id"], "crs": baseline["crs"], "rows": baseline["shape"][0], "columns": baseline["shape"][1]},
        "quality": {"joint_valid_pixels": valid_pixels, "total_pixels": total_pixels, "joint_valid_fraction": round(valid_pixels / total_pixels, 8), "mask_policy": "pixel must be valid in both scenes; zero-denominator index pixels excluded"},
        "thresholds": {"min_valid_fraction": float(min_valid_fraction), "min_abs_ndvi_delta": float(min_abs_ndvi_delta), "min_abs_ndwi_delta": float(min_abs_ndwi_delta)},
        "summary": summaries,
        "pixel_arrays": index_values,
        "interpretation": {
            "status": "HUMAN_REVIEW_REQUIRED",
            "environmental_conclusion": None,
            "regulatory_conclusion": None,
            "violation": None,
            "enforcement_action": None,
            "limitations": [
                "Input arrays must already be decoded, normalized reflectance values with validated band scaling.",
                "No GeoTIFF reading, reprojection, resampling, geospatial topology, or provider authenticity validation is performed.",
                "NDVI/NDWI thresholds are screening defaults, not scientifically calibrated local thresholds.",
                "Cloud-mask provenance, seasonal comparability, sensor processing level and AOI boundary still require independent review.",
                "A spectral candidate is not proof of wetland loss, cause, legal boundary, or violation.",
            ],
        },
    }
    payload["fingerprint"] = _digest(payload)
    return payload


def validate_paired_array_analysis(result: Any) -> dict[str, Any]:
    """Verify output fingerprint and ensure analysis cannot imply a legal conclusion."""
    if not isinstance(result, Mapping):
        return {"valid": False, "findings": [{"code": "INVALID_ANALYSIS_RESULT"}]}
    findings: list[dict[str, str]] = []
    supplied = result.get("fingerprint")
    try:
        payload = dict(result)
        payload.pop("fingerprint", None)
        expected = _digest(payload)
        if not isinstance(supplied, str) or supplied != expected:
            findings.append({"code": "ANALYSIS_FINGERPRINT_MISMATCH"})
    except (TypeError, ValueError):
        findings.append({"code": "ANALYSIS_NOT_CANONICAL_JSON"})
    if result.get("policy_version") != POLICY_VERSION:
        findings.append({"code": "POLICY_VERSION_MISMATCH"})
    if result.get("state") != "PIXEL_ANALYSIS_COMPLETE":
        findings.append({"code": "ANALYSIS_STATE_NOT_COMPLETE"})
    interpretation = result.get("interpretation")
    if not isinstance(interpretation, Mapping):
        findings.append({"code": "INTERPRETATION_REQUIRED"})
    else:
        if interpretation.get("environmental_conclusion") is not None:
            findings.append({"code": "ENVIRONMENTAL_CONCLUSION_MUST_REMAIN_UNSET"})
        if interpretation.get("regulatory_conclusion") is not None:
            findings.append({"code": "REGULATORY_CONCLUSION_MUST_REMAIN_UNSET"})
        if interpretation.get("violation") is not None:
            findings.append({"code": "VIOLATION_MUST_REMAIN_UNSET"})
        if interpretation.get("enforcement_action") is not None:
            findings.append({"code": "ENFORCEMENT_ACTION_MUST_REMAIN_UNSET"})
    return {"valid": not findings, "fingerprint": supplied, "findings": findings}
