"""Safe STAC catalogue discovery for NEMA-AGORA satellite evidence.

Queries a fixed public STAC API for candidate scenes. This module does not
download pixels, compute indices, authenticate reference labels, or infer
environmental violations. Network access is opt-in at the call site.
"""
from __future__ import annotations

from datetime import date
import json
import math
import re
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

STAC_API = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"
POLICY_VERSION = "stac-discovery-v1"
_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class StacDiscoveryError(ValueError):
    """Raised when a STAC search request or response is invalid."""


def _iso_date(value: Any, name: str) -> date:
    if not isinstance(value, str):
        raise StacDiscoveryError(f"{name} must be YYYY-MM-DD.")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise StacDiscoveryError(f"{name} must be YYYY-MM-DD.") from exc
    if result.isoformat() != value:
        raise StacDiscoveryError(f"{name} must use YYYY-MM-DD.")
    return result


def validate_search(*, aoi_id: Any, bbox: Any, start_date: Any, end_date: Any,
                    max_cloud_cover_pct: Any = 30.0, limit: Any = 20) -> dict[str, Any]:
    findings = []
    if not isinstance(aoi_id, str) or not _ID.fullmatch(aoi_id):
        findings.append("aoi_id must be a simple stable identifier.")
    if (not isinstance(bbox, (list, tuple)) or len(bbox) != 4
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)) for v in bbox)):
        findings.append("bbox must contain four finite numbers: west,south,east,north.")
    else:
        west, south, east, north = map(float, bbox)
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            findings.append("bbox coordinates are out of range or have invalid ordering.")
    try:
        start = _iso_date(start_date, "start_date")
        end = _iso_date(end_date, "end_date")
        if end < start:
            findings.append("end_date must not precede start_date.")
    except StacDiscoveryError as exc:
        findings.append(str(exc))
        start = end = None
    if isinstance(max_cloud_cover_pct, bool) or not isinstance(max_cloud_cover_pct, (int, float)) or not math.isfinite(float(max_cloud_cover_pct)) or not 0 <= float(max_cloud_cover_pct) <= 100:
        findings.append("max_cloud_cover_pct must be finite and between 0 and 100.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        findings.append("limit must be an integer between 1 and 100.")
    if findings:
        raise StacDiscoveryError(" ".join(findings))
    return {
        "aoi_id": aoi_id,
        "bbox": [float(v) for v in bbox],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "max_cloud_cover_pct": float(max_cloud_cover_pct),
        "limit": limit,
    }


def _asset_summary(assets: Any) -> dict[str, Any]:
    if not isinstance(assets, Mapping):
        return {}
    output = {}
    for key, asset in assets.items():
        if not isinstance(key, str) or not isinstance(asset, Mapping):
            continue
        href = asset.get("href")
        parsed = urlparse(href) if isinstance(href, str) else None
        if parsed and parsed.scheme == "https" and parsed.netloc and parsed.username is None and parsed.password is None:
            output[key] = {
                "href": href,
                "type": asset.get("type") if isinstance(asset.get("type"), str) else None,
                "roles": asset.get("roles") if isinstance(asset.get("roles"), list) else [],
                "checksum": asset.get("checksum:multihash") or asset.get("file:checksum"),
            }
    return output


def normalize_stac_feature(feature: Mapping[str, Any]) -> dict[str, Any]:
    """Keep a conservative metadata subset and safe HTTPS asset references."""
    if not isinstance(feature, Mapping):
        raise StacDiscoveryError("STAC feature must be an object.")
    properties = feature.get("properties")
    if not isinstance(properties, Mapping):
        properties = {}
    item_id = feature.get("id")
    collection = feature.get("collection")
    if not isinstance(item_id, str) or not item_id.strip():
        raise StacDiscoveryError("STAC feature has no id.")
    if collection != COLLECTION:
        raise StacDiscoveryError("STAC feature is not from the configured Sentinel-2 L2A collection.")
    acquired = properties.get("datetime") or properties.get("start_datetime")
    cloud = properties.get("eo:cloud_cover")
    if isinstance(cloud, bool) or not isinstance(cloud, (int, float)) or not math.isfinite(float(cloud)) or not 0 <= float(cloud) <= 100:
        cloud = None
    return {
        "item_id": item_id,
        "collection": collection,
        "acquired_at": acquired if isinstance(acquired, str) else None,
        "cloud_cover_pct": float(cloud) if cloud is not None else None,
        "platform": properties.get("platform") if isinstance(properties.get("platform"), str) else None,
        "processing_level": properties.get("s2:processing_baseline"),
        "geometry": feature.get("geometry") if isinstance(feature.get("geometry"), Mapping) else None,
        "assets": _asset_summary(feature.get("assets")),
        "provenance": {
            "provider": "Earth Search STAC",
            "catalogue_api": STAC_API,
            "collection": COLLECTION,
            "discovery_policy_version": POLICY_VERSION,
            "pixel_downloaded": False,
            "indices_computed": False,
        },
    }


def discover_scenes(*, aoi_id: str, bbox: list[float], start_date: str,
                    end_date: str, max_cloud_cover_pct: float = 30.0,
                    limit: int = 20, request_json: Callable[..., Any] | None = None) -> dict[str, Any]:
    """Search a fixed public STAC endpoint; injectable requester enables offline tests."""
    query = validate_search(aoi_id=aoi_id, bbox=bbox, start_date=start_date,
                            end_date=end_date, max_cloud_cover_pct=max_cloud_cover_pct, limit=limit)
    if request_json is None:
        try:
            import requests
        except ImportError as exc:
            raise StacDiscoveryError("The requests package is required for online catalogue discovery.") from exc

        def request_json(url: str, *, payload: dict[str, Any], timeout: float) -> Any:
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()

    payload = {
        "collections": [COLLECTION],
        "bbox": query["bbox"],
        "datetime": f'{query["start_date"]}T00:00:00Z/{query["end_date"]}T23:59:59Z',
        "limit": query["limit"],
        "query": {"eo:cloud_cover": {"lte": query["max_cloud_cover_pct"]}},
    }
    try:
        response = request_json(f"{STAC_API}/search", payload=payload, timeout=20.0)
    except Exception as exc:
        raise StacDiscoveryError(f"Catalogue request failed ({type(exc).__name__}); no imagery was downloaded.") from exc
    if not isinstance(response, Mapping) or not isinstance(response.get("features"), list):
        raise StacDiscoveryError("Catalogue returned an invalid STAC FeatureCollection.")
    scenes, rejected = [], []
    for feature in response["features"][:query["limit"]]:
        try:
            scene = normalize_stac_feature(feature)
            if scene["cloud_cover_pct"] is None:
                rejected.append({"item_id": scene["item_id"], "reason": "MISSING_OR_INVALID_CLOUD_COVER"})
            elif scene["cloud_cover_pct"] > query["max_cloud_cover_pct"]:
                rejected.append({"item_id": scene["item_id"], "reason": "CLOUD_COVER_ABOVE_THRESHOLD"})
            else:
                scenes.append(scene)
        except StacDiscoveryError as exc:
            rejected.append({"item_id": feature.get("id") if isinstance(feature, Mapping) else None, "reason": str(exc)})
    report = {
        "policy_version": POLICY_VERSION,
        "state": "SCENES_FOUND_REQUIRING_ASSET_REVIEW" if scenes else "NO_QUALIFYING_SCENES",
        "search": query,
        "catalogue": {"api": STAC_API, "collection": COLLECTION, "returned_features": len(response["features"])},
        "scenes": scenes,
        "rejected": rejected,
        "limitations": [
            "Catalogue metadata is not proof that asset URLs remain available or pixels are valid.",
            "Scene-level cloud cover is not an AOI-specific valid-pixel fraction.",
            "No pixel assets were downloaded and no NDVI/NDWI values or environmental conclusions were computed.",
            "Check acquisition time, AOI coverage, projection/grid, processing baseline, cloud masks and checksums before analysis.",
        ],
    }
    report["report_sha256"] = __import__("hashlib").sha256(json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()).hexdigest()
    return report
