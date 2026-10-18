"""Phase 60 — NEMA-AGORA spatial/temporal evidence quality gates."""
from __future__ import annotations
import hashlib, json, math, re
from typing import Any, Mapping

POLICY_VERSION = "phase60-v1"
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_ALIGNMENT = {"ALIGNED", "UNVERIFIED", "MISMATCHED"}

def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()).hexdigest()

def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))

def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))

def _bounded(value: Any, low: float, high: float) -> bool:
    return _finite(value) and low <= float(value) <= high

def validate_change_quality(*, baseline_aoi_id: Any, comparison_aoi_id: Any, baseline_grid_id: Any,
                            comparison_grid_id: Any, spatial_alignment: Any, spatial_resolution_m: Any,
                            baseline_cloud_cover_pct: Any, comparison_cloud_cover_pct: Any,
                            baseline_valid_fraction: Any, comparison_valid_fraction: Any,
                            ndvi_uncertainty: Any, ndwi_uncertainty: Any,
                            max_cloud_cover_pct: float = 30.0, min_valid_fraction: float = 0.70) -> dict[str, Any]:
    findings = []
    if not _valid_id(baseline_aoi_id): findings.append({"code": "INVALID_BASELINE_AOI_ID"})
    if not _valid_id(comparison_aoi_id): findings.append({"code": "INVALID_COMPARISON_AOI_ID"})
    if _valid_id(baseline_aoi_id) and _valid_id(comparison_aoi_id) and baseline_aoi_id != comparison_aoi_id:
        findings.append({"code": "AOI_ID_MISMATCH"})
    if not _valid_id(baseline_grid_id): findings.append({"code": "INVALID_BASELINE_GRID_ID"})
    if not _valid_id(comparison_grid_id): findings.append({"code": "INVALID_COMPARISON_GRID_ID"})
    if _valid_id(baseline_grid_id) and _valid_id(comparison_grid_id) and baseline_grid_id != comparison_grid_id:
        findings.append({"code": "GRID_ID_MISMATCH"})
    if spatial_alignment not in _ALIGNMENT:
        findings.append({"code": "INVALID_SPATIAL_ALIGNMENT"})
    elif spatial_alignment != "ALIGNED":
        findings.append({"code": f"SPATIAL_ALIGNMENT_{spatial_alignment}"})
    if not _finite(spatial_resolution_m) or float(spatial_resolution_m) <= 0:
        findings.append({"code": "INVALID_SPATIAL_RESOLUTION"})
    for label, value in (("BASELINE", baseline_cloud_cover_pct), ("COMPARISON", comparison_cloud_cover_pct)):
        if not _bounded(value, 0.0, 100.0): findings.append({"code": f"INVALID_{label}_CLOUD_COVER"})
        elif float(value) > float(max_cloud_cover_pct): findings.append({"code": f"{label}_CLOUD_COVER_ABOVE_THRESHOLD"})
    for label, value in (("BASELINE", baseline_valid_fraction), ("COMPARISON", comparison_valid_fraction)):
        if not _bounded(value, 0.0, 1.0): findings.append({"code": f"INVALID_{label}_VALID_FRACTION"})
        elif float(value) < float(min_valid_fraction): findings.append({"code": f"{label}_VALID_FRACTION_BELOW_THRESHOLD"})
    for name, value in (("NDVI", ndvi_uncertainty), ("NDWI", ndwi_uncertainty)):
        if not _finite(value) or float(value) < 0: findings.append({"code": f"INVALID_{name}_UNCERTAINTY"})
    if not _finite(max_cloud_cover_pct) or not 0.0 <= float(max_cloud_cover_pct) <= 100.0:
        findings.append({"code": "INVALID_MAX_CLOUD_THRESHOLD"})
    if not _finite(min_valid_fraction) or not 0.0 <= float(min_valid_fraction) <= 1.0:
        findings.append({"code": "INVALID_MIN_VALID_FRACTION"})
    return {"policy_version": POLICY_VERSION, "state": "VALID" if not findings else "CONTROL_REQUIRED", "findings": findings}

def spatial_temporal_quality_evidence(*, change_evidence: Mapping[str, Any],
                                      baseline_aoi_id: str, comparison_aoi_id: str,
                                      baseline_grid_id: str, comparison_grid_id: str,
                                      spatial_alignment: str, spatial_resolution_m: float,
                                      baseline_cloud_cover_pct: float, comparison_cloud_cover_pct: float,
                                      baseline_valid_fraction: float, comparison_valid_fraction: float,
                                      ndvi_uncertainty: float, ndwi_uncertainty: float,
                                      max_cloud_cover_pct: float = 30.0, min_valid_fraction: float = 0.70) -> dict[str, Any]:
    if not isinstance(change_evidence, Mapping):
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED", "findings": [{"code": "INVALID_CHANGE_EVIDENCE"}]}
    findings = []
    if change_evidence.get("state") != "CANDIDATE_CHANGE_EVIDENCE":
        findings.append({"code": "INVALID_CHANGE_EVIDENCE_STATE"})
    validation = validate_change_quality(
        baseline_aoi_id=baseline_aoi_id, comparison_aoi_id=comparison_aoi_id,
        baseline_grid_id=baseline_grid_id, comparison_grid_id=comparison_grid_id,
        spatial_alignment=spatial_alignment, spatial_resolution_m=spatial_resolution_m,
        baseline_cloud_cover_pct=baseline_cloud_cover_pct, comparison_cloud_cover_pct=comparison_cloud_cover_pct,
        baseline_valid_fraction=baseline_valid_fraction, comparison_valid_fraction=comparison_valid_fraction,
        ndvi_uncertainty=ndvi_uncertainty, ndwi_uncertainty=ndwi_uncertainty,
        max_cloud_cover_pct=max_cloud_cover_pct, min_valid_fraction=min_valid_fraction)
    findings.extend(validation["findings"])
    if findings:
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED", "findings": findings}
    payload = {
        "policy_version": POLICY_VERSION, "state": "CANDIDATE_CHANGE_EVIDENCE",
        "change_fingerprint": change_evidence.get("fingerprint"),
        "spatial": {"baseline_aoi_id": baseline_aoi_id, "comparison_aoi_id": comparison_aoi_id,
                    "baseline_grid_id": baseline_grid_id, "comparison_grid_id": comparison_grid_id,
                    "spatial_alignment": spatial_alignment, "spatial_resolution_m": float(spatial_resolution_m)},
        "quality": {"baseline_cloud_cover_pct": float(baseline_cloud_cover_pct),
                    "comparison_cloud_cover_pct": float(comparison_cloud_cover_pct),
                    "baseline_valid_fraction": float(baseline_valid_fraction),
                    "comparison_valid_fraction": float(comparison_valid_fraction),
                    "thresholds": {"max_cloud_cover_pct": float(max_cloud_cover_pct),
                                   "min_valid_fraction": float(min_valid_fraction)}},
        "uncertainty": {"ndvi_uncertainty": float(ndvi_uncertainty), "ndwi_uncertainty": float(ndwi_uncertainty),
                        "method": "UPSTREAM_PROVIDED"},
        "interpretation": {"status": "HUMAN_REVIEW_REQUIRED", "evidence_quality": "ACCEPTED_FOR_REVIEW",
                           "environmental_conclusion": None, "regulatory_conclusion": None}}
    payload["fingerprint"] = fingerprint(payload)
    return payload
