"""Fail-closed validation for user-supplied WGS84 GeoJSON areas of interest.

This validates basic structure and coordinate bounds only. It does not prove geometry
topology, legal boundaries, positional accuracy, or that a polygon is an authorised AOI.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any

MAX_COORDINATES = 100_000
MAX_FEATURES = 100


def _position(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    lon, lat = value[0], value[1]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in (lon, lat)):
        return None
    if not math.isfinite(float(lon)) or not math.isfinite(float(lat)):
        return None
    if not -180 <= float(lon) <= 180 or not -90 <= float(lat) <= 90:
        return None
    return float(lon), float(lat)


def validate_geojson_aoi(document: Any) -> dict[str, Any]:
    """Validate Polygon/MultiPolygon GeoJSON and return coordinate bounds."""
    findings: list[dict[str, str]] = []
    if isinstance(document, str):
        try:
            document = json.loads(document)
        except (json.JSONDecodeError, TypeError):
            return {"valid": False, "findings": [{"code": "INVALID_JSON"}]}
    if not isinstance(document, Mapping):
        return {"valid": False, "findings": [{"code": "DOCUMENT_MUST_BE_OBJECT"}]}

    kind = document.get("type")
    geometries: list[Mapping[str, Any]] = []
    if kind == "Feature":
        geometry = document.get("geometry")
        if isinstance(geometry, Mapping):
            geometries = [geometry]
        else:
            findings.append({"code": "FEATURE_GEOMETRY_REQUIRED"})
    elif kind == "FeatureCollection":
        features = document.get("features")
        if not isinstance(features, list) or not features:
            findings.append({"code": "FEATURES_REQUIRED"})
        elif len(features) > MAX_FEATURES:
            findings.append({"code": "FEATURE_LIMIT_EXCEEDED"})
        else:
            for index, feature in enumerate(features):
                if not isinstance(feature, Mapping) or feature.get("type") != "Feature":
                    findings.append({"code": f"FEATURE_{index}_INVALID"})
                elif not isinstance(feature.get("geometry"), Mapping):
                    findings.append({"code": f"FEATURE_{index}_GEOMETRY_REQUIRED"})
                else:
                    geometries.append(feature["geometry"])
    elif kind in {"Polygon", "MultiPolygon"}:
        geometries = [document]
    else:
        findings.append({"code": "UNSUPPORTED_GEOJSON_TYPE"})

    all_positions: list[tuple[float, float]] = []
    coordinate_count = 0

    def walk_ring(ring: Any, path: str) -> None:
        nonlocal coordinate_count
        if not isinstance(ring, list) or len(ring) < 4:
            findings.append({"code": f"{path}_RING_TOO_SHORT"})
            return
        positions: list[tuple[float, float]] = []
        for position in ring:
            coordinate_count += 1
            parsed = _position(position)
            if parsed is None:
                findings.append({"code": f"{path}_INVALID_POSITION"})
            else:
                positions.append(parsed)
                all_positions.append(parsed)
        if len(positions) >= 4 and positions[0] != positions[-1]:
            findings.append({"code": f"{path}_RING_NOT_CLOSED"})
        if len(set(positions[:-1])) < 3:
            findings.append({"code": f"{path}_INSUFFICIENT_UNIQUE_VERTICES"})

    for g_index, geometry in enumerate(geometries):
        g_type = geometry.get("type")
        coords = geometry.get("coordinates")
        if g_type == "Polygon":
            if not isinstance(coords, list) or not coords:
                findings.append({"code": f"GEOMETRY_{g_index}_POLYGON_RINGS_REQUIRED"})
            else:
                for r_index, ring in enumerate(coords):
                    walk_ring(ring, f"GEOMETRY_{g_index}_RING_{r_index}")
        elif g_type == "MultiPolygon":
            if not isinstance(coords, list) or not coords:
                findings.append({"code": f"GEOMETRY_{g_index}_POLYGONS_REQUIRED"})
            else:
                for p_index, polygon in enumerate(coords):
                    if not isinstance(polygon, list) or not polygon:
                        findings.append({"code": f"GEOMETRY_{g_index}_POLYGON_{p_index}_RINGS_REQUIRED"})
                    else:
                        for r_index, ring in enumerate(polygon):
                            walk_ring(ring, f"GEOMETRY_{g_index}_POLYGON_{p_index}_RING_{r_index}")
        else:
            findings.append({"code": f"GEOMETRY_{g_index}_UNSUPPORTED_TYPE"})

    if coordinate_count > MAX_COORDINATES:
        findings.append({"code": "COORDINATE_LIMIT_EXCEEDED"})
    if not all_positions:
        findings.append({"code": "NO_VALID_COORDINATES"})

    result: dict[str, Any] = {
        "valid": not findings,
        "geometry_count": len(geometries),
        "coordinate_count": coordinate_count,
        "coordinate_reference": "WGS84 longitude/latitude (GeoJSON default)",
        "findings": findings,
        "limitations": [
            "Basic structure and coordinate bounds only; self-intersection and topology are not fully checked.",
            "The polygon is not verified as an official or authorised environmental boundary.",
            "Coordinate bounds are not a geodesic area calculation.",
        ],
    }
    if all_positions:
        lons = [p[0] for p in all_positions]
        lats = [p[1] for p in all_positions]
        result["bounds"] = {
            "west": min(lons), "south": min(lats),
            "east": max(lons), "north": max(lats),
        }
    return result
