"""Phase 56 — NEMA-AGORA provider-neutral spatial intelligence foundation."""
from __future__ import annotations
import hashlib, json, math, re
from typing import Any, Mapping

POLICY_VERSION = "phase56-v1"
AOI_TYPES = {"DISTRICT", "WETLAND", "WATERSHED", "PROTECTED_AREA", "CUSTOM"}
GEOMETRY_TYPES = {"Point", "Polygon", "MultiPolygon"}
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()).hexdigest()

def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))

def validate_coordinate(latitude: Any, longitude: Any) -> list[dict[str, str]]:
    findings = []
    if isinstance(latitude, bool) or not isinstance(latitude, (int, float)) or not math.isfinite(float(latitude)):
        findings.append({"code": "INVALID_LATITUDE"})
    elif not -90 <= float(latitude) <= 90:
        findings.append({"code": "LATITUDE_OUT_OF_RANGE"})
    if isinstance(longitude, bool) or not isinstance(longitude, (int, float)) or not math.isfinite(float(longitude)):
        findings.append({"code": "INVALID_LONGITUDE"})
    elif not -180 <= float(longitude) <= 180:
        findings.append({"code": "LONGITUDE_OUT_OF_RANGE"})
    return findings

def validate_geometry(geometry: Any) -> list[dict[str, str]]:
    if not isinstance(geometry, Mapping):
        return [{"code": "INVALID_GEOMETRY"}]
    findings = []
    if geometry.get("type") not in GEOMETRY_TYPES:
        findings.append({"code": "UNSUPPORTED_GEOMETRY_TYPE"})
    if geometry.get("coordinates") is None:
        findings.append({"code": "MISSING_COORDINATES"})
    return findings

def validate_aoi(aoi: Mapping[str, Any]) -> dict[str, Any]:
    findings = []
    if not _valid_id(aoi.get("aoi_id")):
        findings.append({"code": "INVALID_AOI_ID"})
    if not isinstance(aoi.get("name"), str) or not aoi.get("name").strip():
        findings.append({"code": "INVALID_AOI_NAME"})
    if aoi.get("type") not in AOI_TYPES:
        findings.append({"code": "INVALID_AOI_TYPE"})
    if aoi.get("crs") != "EPSG:4326":
        findings.append({"code": "UNSUPPORTED_CRS"})
    findings.extend(validate_geometry(aoi.get("geometry")))
    return {"state": "CONTROL_REQUIRED" if findings else "VALID", "findings": findings}

def validate_spatial_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    findings = []
    if not _valid_id(observation.get("observation_id")):
        findings.append({"code": "INVALID_OBSERVATION_ID"})
    findings.extend(validate_coordinate(observation.get("latitude"), observation.get("longitude")))
    if observation.get("crs") != "EPSG:4326":
        findings.append({"code": "UNSUPPORTED_CRS"})
    if not isinstance(observation.get("source"), str) or not observation.get("source").strip():
        findings.append({"code": "MISSING_SOURCE"})
    if not isinstance(observation.get("captured_at"), str) or not observation.get("captured_at").strip():
        findings.append({"code": "MISSING_CAPTURE_TIMESTAMP"})
    return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED" if findings else "VALID", "findings": findings, "observation_fingerprint": fingerprint(dict(observation))}

def spatial_observation(observation_id: str, latitude: float, longitude: float, source: str, captured_at: str, *, case_id: str | None = None, accuracy_m: float | None = None) -> dict[str, Any]:
    row = {"observation_id": observation_id, "case_id": case_id, "latitude": latitude, "longitude": longitude, "geometry": {"type": "Point", "coordinates": [longitude, latitude]}, "crs": "EPSG:4326", "spatial_accuracy_m": accuracy_m, "captured_at": captured_at, "source": source}
    result = validate_spatial_observation(row)
    if result["state"] != "VALID":
        raise ValueError("Invalid spatial observation: " + json.dumps(result["findings"], sort_keys=True))
    return row

def aoi(aoi_id: str, name: str, aoi_type: str, geometry: Mapping[str, Any]) -> dict[str, Any]:
    row = {"aoi_id": aoi_id, "name": name, "type": aoi_type, "geometry": dict(geometry), "crs": "EPSG:4326", "metadata": {}}
    result = validate_aoi(row)
    if result["state"] != "VALID":
        raise ValueError("Invalid AOI: " + json.dumps(result["findings"], sort_keys=True))
    return row

class SpatialAnalysisProvider:
    """Provider-neutral contract; concrete providers return evidence, not conclusions."""
    provider_name = "abstract"
    def analyze(self, observation: Mapping[str, Any], area_of_interest: Mapping[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Concrete spatial providers must implement analyze().")

def spatial_analysis_contract(result: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {"provider", "analysis_type", "source_ids", "evidence", "confidence", "metadata"}
    findings = []
    if not isinstance(result.get("provider"), str) or not result.get("provider"):
        findings.append({"code": "MISSING_PROVIDER"})
    if not isinstance(result.get("analysis_type"), str) or not result.get("analysis_type"):
        findings.append({"code": "MISSING_ANALYSIS_TYPE"})
    if not isinstance(result.get("source_ids"), list):
        findings.append({"code": "INVALID_SOURCE_IDS"})
    if any(k in result for k in ("conclusion", "violation", "enforcement_action")):
        findings.append({"code": "AUTONOMOUS_CONCLUSION_FORBIDDEN"})
    unknown = sorted(set(result) - allowed)
    if unknown:
        findings.append({"code": "UNEXPECTED_FIELDS", "fields": ",".join(unknown)})
    return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED" if findings else "VALID", "findings": findings}
