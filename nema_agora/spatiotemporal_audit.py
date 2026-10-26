"""Conservative spatial/temporal overlap audit for declared evaluation units.

Bounding-box and date-range overlap are warning/block signals, not proof that
two observations are duplicates. Coordinates must be WGS84 longitude/latitude.
"""
from __future__ import annotations

from datetime import datetime
from itertools import combinations
from typing import Any, Mapping, Sequence


class SpatiotemporalAuditError(ValueError):
    """Raised when spatial/temporal audit metadata is malformed."""


_SPLITS = {"development", "validation", "holdout"}


def _instant(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise SpatiotemporalAuditError(f"{field} must be an ISO timestamp with timezone.")
    try:
        result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise SpatiotemporalAuditError(f"{field} must be an ISO timestamp with timezone.") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise SpatiotemporalAuditError(f"{field} must include a timezone.")
    return result


def _bbox(value: Any, field: str) -> tuple[float, float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise SpatiotemporalAuditError(f"{field} must be [min_lon, min_lat, max_lon, max_lat].")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in value):
        raise SpatiotemporalAuditError(f"{field} values must be numeric.")
    west, south, east, north = map(float, value)
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise SpatiotemporalAuditError(f"{field} must be a valid non-wrapping WGS84 bounding box.")
    return west, south, east, north


def audit_spatiotemporal_separation(units: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Flag cross-split bounding-box intersections and overlapping date intervals."""
    if not isinstance(units, Sequence) or isinstance(units, (str, bytes)) or not units:
        raise SpatiotemporalAuditError("units must be a non-empty array.")
    normalized = []
    seen = set()
    for index, item in enumerate(units):
        if not isinstance(item, Mapping):
            raise SpatiotemporalAuditError(f"units[{index}] must be an object.")
        unit_id, split = item.get("unit_id"), item.get("split")
        if not isinstance(unit_id, str) or not unit_id.strip():
            raise SpatiotemporalAuditError(f"units[{index}].unit_id is required.")
        unit_id = unit_id.strip()
        if unit_id in seen:
            raise SpatiotemporalAuditError(f"duplicate unit_id: {unit_id}.")
        seen.add(unit_id)
        if split not in _SPLITS:
            raise SpatiotemporalAuditError(f"units[{index}].split must be development, validation, or holdout.")
        bbox = _bbox(item.get("bbox_wgs84"), f"units[{index}].bbox_wgs84")
        start = _instant(item.get("observation_start"), f"units[{index}].observation_start")
        end = _instant(item.get("observation_end"), f"units[{index}].observation_end")
        if end < start:
            raise SpatiotemporalAuditError(f"units[{index}].observation_end precedes observation_start.")
        normalized.append({"unit_id": unit_id, "split": split, "bbox": bbox, "start": start, "end": end})
    findings = []
    for left, right in combinations(normalized, 2):
        if left["split"] == right["split"]:
            continue
        a, b = left["bbox"], right["bbox"]
        spatial_overlap = a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
        temporal_overlap = left["start"] <= right["end"] and right["start"] <= left["end"]
        if spatial_overlap or temporal_overlap:
            findings.append({
                "left_unit_id": left["unit_id"], "left_split": left["split"],
                "right_unit_id": right["unit_id"], "right_split": right["split"],
                "bounding_boxes_intersect": spatial_overlap,
                "observation_intervals_overlap": temporal_overlap,
                "finding": "SPATIAL_AND_TEMPORAL_OVERLAP" if spatial_overlap and temporal_overlap else
                           "SPATIAL_OVERLAP" if spatial_overlap else "TEMPORAL_OVERLAP",
            })
    return {
        "schema_version": "nema-spatiotemporal-separation-v1",
        "state": "BLOCKED_POTENTIAL_CROSS_SPLIT_LEAKAGE" if findings else "NO_DECLARED_BBOX_OR_INTERVAL_OVERLAP",
        "decision": "REVIEW_AND_BLOCK_UNTIL_RESOLVED" if findings else "NO_DECLARED_OVERLAP_FOUND",
        "unit_count": len(normalized),
        "finding_count": len(findings),
        "findings": findings,
        "limitations": [
            "Bounding-box intersections and overlapping observation intervals are conservative indicators, not proof of duplicated samples.",
            "No finding does not prove spatial or temporal independence: nearby buffers, shared tiles/assets, derived features, aliases, and tuning history are not assessed.",
            "Bounding boxes must be WGS84, non-wrapping longitude/latitude extents. Dateline-crossing geometries require preprocessing by a trusted GIS workflow.",
        ],
    }
