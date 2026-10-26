"""Evidence manifest validation for reproducible NEMA-AGORA satellite evaluations.

Validates metadata completeness only; it does not verify imagery, labels,
geospatial alignment, or representativeness of a reference sample.
"""
from __future__ import annotations
from datetime import date
import math
import hashlib
import json
import re
from typing import Any, Mapping

MANIFEST_SCHEMA_VERSION = "satellite-dataset-manifest-v1"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
_REQUIRED = (
    "dataset_id", "aoi_id", "sensor", "product_id", "processing_version",
    "crs", "grid_id", "reference_set_id", "reference_set_version",
    "sampling_method", "label_review_method", "candidate_policy_version",
    "split", "acquisition_start", "acquisition_end", "cloud_filter_method",
    "valid_pixel_method", "spatial_resolution_m",
)
_ALLOWED_SPLITS = {"development", "validation", "holdout"}


class SatelliteManifestError(ValueError):
    """Raised when manifest metadata is incomplete or inconsistent."""


def _iso_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise SatelliteManifestError(f"{field} must be an ISO date (YYYY-MM-DD).")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SatelliteManifestError(f"{field} must be an ISO date (YYYY-MM-DD).") from exc
    if parsed.isoformat() != value:
        raise SatelliteManifestError(f"{field} must use canonical YYYY-MM-DD format.")
    return parsed


def validate_dataset_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Validate provenance metadata and return a canonical manifest digest."""
    if not isinstance(manifest, Mapping):
        raise SatelliteManifestError("manifest must be an object.")
    missing = [key for key in _REQUIRED if key not in manifest]
    if missing:
        raise SatelliteManifestError("missing required fields: " + ", ".join(missing))
    for key in _REQUIRED:
        value = manifest[key]
        if not isinstance(value, str) or not value.strip():
            raise SatelliteManifestError(f"{key} must be a non-empty string.")
        if key in {"dataset_id", "aoi_id", "grid_id", "reference_set_id", "reference_set_version", "candidate_policy_version"} and not _ID.fullmatch(value.strip()):
            raise SatelliteManifestError(f"{key} contains unsupported identifier characters.")
    if manifest["split"] not in _ALLOWED_SPLITS:
        raise SatelliteManifestError("split must be development, validation, or holdout.")
    start = _iso_date(manifest["acquisition_start"], "acquisition_start")
    end = _iso_date(manifest["acquisition_end"], "acquisition_end")
    if end < start:
        raise SatelliteManifestError("acquisition_end must not precede acquisition_start.")
    resolution = manifest["spatial_resolution_m"]
    if isinstance(resolution, bool) or not isinstance(resolution, (int, float)) or not math.isfinite(float(resolution)) or resolution <= 0:
        raise SatelliteManifestError("spatial_resolution_m must be a positive number.")
    for field, upper in (("cloud_cover_pct", 100.0), ("valid_pixel_fraction", 1.0)):
        value = manifest.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise SatelliteManifestError(f"{field} must be supplied as a numeric quality value.")
        if not 0 <= value <= upper:
            raise SatelliteManifestError(f"{field} must be between 0 and {upper}.")
    digest = manifest.get("source_sha256")
    if digest is not None and (not isinstance(digest, str) or not _SHA256.fullmatch(digest)):
        raise SatelliteManifestError("source_sha256, when supplied, must be a 64-character hex digest.")
    canonical = dict(manifest)
    canonical["schema_version"] = MANIFEST_SCHEMA_VERSION
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "state": "METADATA_COMPLETE_NOT_INDEPENDENTLY_VERIFIED",
        "manifest": canonical,
        "manifest_sha256": hashlib.sha256(encoded).hexdigest(),
        "warnings": [
            "Completeness checks do not verify source assets or their metadata.",
            "Holdout designation is a declaration, not proof that tuning did not use holdout data.",
            "Reference labels, sample representativeness, spatial alignment, and quality filters require independent review.",
        ],
    }
