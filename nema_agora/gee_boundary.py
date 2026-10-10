"""Phase 70 — fail-closed Google Earth Engine integration boundary.

This module deliberately has no Earth Engine SDK dependency and performs no network
calls. A separately configured provider adapter must be injected at execution time.
"""
from __future__ import annotations
from datetime import date
from typing import Any, Mapping, Protocol
from .aoi_registry import validate_asset

POLICY_VERSION = "phase70-v1"
MAX_DATE_WINDOW_DAYS = 90
MAX_CLOUD_PERCENT = 100.0
COLLECTIONS = {"SENTINEL2_SR_HARMONIZED": "COPERNICUS/S2_SR_HARMONIZED"}

class SceneProvider(Protocol):
    """Adapter contract for provider-sourced scene metadata."""
    def list_scenes(self, request: Mapping[str, Any]) -> Any: ...

def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None

def _valid_position(position: Any) -> bool:
    return (isinstance(position, (list, tuple)) and len(position) >= 2
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in position[:2])
            and -180 <= position[0] <= 180 and -90 <= position[1] <= 90)

def _valid_ring(ring: Any) -> bool:
    return (isinstance(ring, (list, tuple)) and len(ring) >= 4
            and all(_valid_position(p) for p in ring)
            and list(ring[0][:2]) == list(ring[-1][:2]))

def _valid_geometry(geometry: Any) -> bool:
    if not isinstance(geometry, Mapping):
        return False
    kind, coordinates = geometry.get("type"), geometry.get("coordinates")
    if kind == "Polygon":
        return isinstance(coordinates, (list, tuple)) and bool(coordinates) and all(_valid_ring(r) for r in coordinates)
    if kind == "MultiPolygon":
        return (isinstance(coordinates, (list, tuple)) and bool(coordinates)
                and all(isinstance(poly, (list, tuple)) and bool(poly)
                        and all(_valid_ring(r) for r in poly) for poly in coordinates))
    return False

def validate_scene_request(asset: Mapping[str, Any], start_date: str, end_date: str, *,
                           collection: str = "SENTINEL2_SR_HARMONIZED",
                           cloud_max: float = 30.0) -> dict[str, Any]:
    """Validate a governed AOI and bounded query; never contact Earth Engine."""
    findings: list[dict[str, str]] = []
    if not isinstance(asset, Mapping):
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED",
                "findings": [{"code": "INVALID_AOI"}]}
    if validate_asset(asset).get("state") != "VALID":
        findings.append({"code": "AOI_NOT_GOVERNED"})
    if asset.get("crs") != "EPSG:4326":
        findings.append({"code": "UNSUPPORTED_CRS"})
    if not _valid_geometry(asset.get("geometry")):
        findings.append({"code": "INVALID_GEOJSON_GEOMETRY"})
    start, end = _parse_date(start_date), _parse_date(end_date)
    if start is None:
        findings.append({"code": "INVALID_START_DATE"})
    if end is None:
        findings.append({"code": "INVALID_END_DATE"})
    if start is not None and end is not None:
        if end < start:
            findings.append({"code": "DATE_RANGE_REVERSED"})
        elif (end - start).days > MAX_DATE_WINDOW_DAYS:
            findings.append({"code": "DATE_WINDOW_TOO_LARGE"})
    if collection not in COLLECTIONS:
        findings.append({"code": "COLLECTION_NOT_ALLOWLISTED"})
    if (not isinstance(cloud_max, (int, float)) or isinstance(cloud_max, bool)
            or not 0 <= cloud_max <= MAX_CLOUD_PERCENT):
        findings.append({"code": "INVALID_CLOUD_THRESHOLD"})
    if findings:
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED", "findings": findings}
    return {"policy_version": POLICY_VERSION, "state": "REQUEST_VALIDATED", "findings": [],
            "request": {"asset_id": asset["asset_id"], "asset_fingerprint": asset.get("asset_fingerprint"),
                        "geometry": dict(asset["geometry"]), "crs": "EPSG:4326",
                        "start_date": start.isoformat(), "end_date_exclusive": end.isoformat(),
                        "collection_key": collection, "collection_id": COLLECTIONS[collection],
                        "cloud_max": float(cloud_max)}}

def execute_scene_request(validated: Mapping[str, Any], *, provider: SceneProvider | None,
                          credentials_configured: bool = False) -> dict[str, Any]:
    """Execute only through an explicitly configured adapter; never invent success."""
    if not isinstance(validated, Mapping) or validated.get("state") != "REQUEST_VALIDATED":
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED",
                "findings": [{"code": "REQUEST_NOT_VALIDATED"}], "scenes": []}
    if not credentials_configured:
        return {"policy_version": POLICY_VERSION, "state": "PROVIDER_NOT_CONFIGURED",
                "findings": [{"code": "EARTH_ENGINE_CREDENTIALS_NOT_CONFIGURED"}], "scenes": []}
    if provider is None or not callable(getattr(provider, "list_scenes", None)):
        return {"policy_version": POLICY_VERSION, "state": "PROVIDER_NOT_CONFIGURED",
                "findings": [{"code": "SCENE_PROVIDER_MISSING"}], "scenes": []}
    try:
        raw_scenes = provider.list_scenes(validated["request"])
    except Exception:
        return {"policy_version": POLICY_VERSION, "state": "PROVIDER_ERROR",
                "findings": [{"code": "SCENE_PROVIDER_FAILED"}], "scenes": []}
    if not isinstance(raw_scenes, (list, tuple)):
        return {"policy_version": POLICY_VERSION, "state": "PROVIDER_ERROR",
                "findings": [{"code": "INVALID_PROVIDER_RESPONSE"}], "scenes": []}
    scenes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for scene in raw_scenes:
        if not isinstance(scene, Mapping):
            return {"policy_version": POLICY_VERSION, "state": "PROVIDER_ERROR",
                    "findings": [{"code": "INVALID_SCENE_METADATA"}], "scenes": []}
        scene_id = scene.get("scene_id")
        acquired = _parse_date(scene.get("acquired_date"))
        cloud = scene.get("cloud_percent")
        if (not isinstance(scene_id, str) or not scene_id.strip() or scene_id in seen
                or acquired is None or not isinstance(cloud, (int, float)) or isinstance(cloud, bool)
                or not 0 <= cloud <= 100):
            return {"policy_version": POLICY_VERSION, "state": "PROVIDER_ERROR",
                    "findings": [{"code": "INVALID_SCENE_METADATA"}], "scenes": []}
        if not (validated["request"]["start_date"] <= acquired.isoformat()
                < validated["request"]["end_date_exclusive"]):
            return {"policy_version": POLICY_VERSION, "state": "PROVIDER_ERROR",
                    "findings": [{"code": "SCENE_OUTSIDE_REQUEST_WINDOW"}], "scenes": []}
        if cloud <= validated["request"]["cloud_max"]:
            scenes.append({"scene_id": scene_id, "acquired_date": acquired.isoformat(),
                           "cloud_percent": float(cloud),
                           "collection_id": validated["request"]["collection_id"],
                           "provider": "google_earth_engine"})
        seen.add(scene_id)
    scenes.sort(key=lambda item: (item["acquired_date"], item["scene_id"]))
    return {"policy_version": POLICY_VERSION, "state": "PROVIDER_QUERY_COMPLETE", "findings": [],
            "asset_id": validated["request"]["asset_id"], "collection_id": validated["request"]["collection_id"],
            "scene_count": len(scenes), "scenes": scenes,
            "evidence_note": "Metadata returned by the configured provider adapter; not a compliance finding."}
