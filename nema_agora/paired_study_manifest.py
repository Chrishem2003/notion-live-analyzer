"""Paired-scene study manifest for reproducible environmental monitoring.

This creates a review-ready manifest from already validated manual asset receipts and a
basic AOI validation report. It does not process raster pixels, fetch provider data, or
infer environmental change.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from nema_agora.asset_receipt import validate_asset_receipt
from nema_agora.geojson_aoi import validate_geojson_aoi

POLICY_VERSION = "paired-study-manifest-v1"


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None


def build_paired_study_manifest(
    *,
    study_id: str,
    aoi_document: Any,
    baseline_receipt: Mapping[str, Any],
    comparison_receipt: Mapping[str, Any],
    processing_notes: str,
) -> dict[str, Any]:
    """Build a deterministic paired-scene manifest only after strict input validation."""
    findings: list[dict[str, str]] = []
    if not isinstance(study_id, str) or not study_id.strip() or len(study_id) > 128:
        findings.append({"code": "INVALID_STUDY_ID"})
    aoi_report = validate_geojson_aoi(aoi_document)
    if not aoi_report.get("valid"):
        findings.append({"code": "AOI_VALIDATION_FAILED"})
    baseline_validation = validate_asset_receipt(baseline_receipt)
    comparison_validation = validate_asset_receipt(comparison_receipt)
    if not baseline_validation.get("valid"):
        findings.append({"code": "BASELINE_RECEIPT_INVALID"})
    if not comparison_validation.get("valid"):
        findings.append({"code": "COMPARISON_RECEIPT_INVALID"})
    if findings:
        raise ValueError("Study manifest inputs failed validation: " + ", ".join(x["code"] for x in findings))

    if baseline_receipt.get("baseline_or_comparison") != "baseline":
        findings.append({"code": "BASELINE_RECEIPT_ROLE_MISMATCH"})
    if comparison_receipt.get("baseline_or_comparison") != "comparison":
        findings.append({"code": "COMPARISON_RECEIPT_ROLE_MISMATCH"})
    for field, code in (
        ("source_id", "SOURCE_ID_MISMATCH"),
        ("aoi_id", "AOI_ID_MISMATCH"),
        ("crs", "CRS_MISMATCH"),
        ("spatial_resolution_m", "SPATIAL_RESOLUTION_MISMATCH"),
    ):
        if baseline_receipt.get(field) != comparison_receipt.get(field):
            findings.append({"code": code})
    baseline_time = _parse_timestamp(baseline_receipt.get("acquired_at"))
    comparison_time = _parse_timestamp(comparison_receipt.get("acquired_at"))
    if baseline_time is None or comparison_time is None:
        findings.append({"code": "INVALID_ACQUISITION_TIME"})
    elif baseline_time == comparison_time:
        findings.append({"code": "SCENES_MUST_HAVE_DIFFERENT_ACQUISITION_TIMES"})
    elif baseline_time > comparison_time:
        findings.append({"code": "BASELINE_MUST_PRECEDE_COMPARISON"})
    baseline_assets = {item["sha256"] for item in baseline_receipt["assets"]}
    comparison_assets = {item["sha256"] for item in comparison_receipt["assets"]}
    if baseline_assets & comparison_assets:
        findings.append({"code": "BASELINE_AND_COMPARISON_ASSETS_OVERLAP"})
    if not isinstance(processing_notes, str) or not processing_notes.strip():
        findings.append({"code": "PROCESSING_NOTES_REQUIRED"})
    if findings:
        raise ValueError("Study manifest inputs failed validation: " + ", ".join(x["code"] for x in findings))

    payload: dict[str, Any] = {
        "policy_version": POLICY_VERSION,
        "study_id": study_id.strip(),
        "study_state": "READY_FOR_PROCESSING_REVIEW",
        "aoi": {
            "validation_state": "BASIC_STRUCTURE_VALID",
            "coordinate_reference": aoi_report["coordinate_reference"],
            "bounds": aoi_report.get("bounds"),
            "geometry_count": aoi_report["geometry_count"],
            "limitations": list(aoi_report["limitations"]),
        },
        "baseline": {
            "receipt_id": baseline_receipt["receipt_id"],
            "source_id": baseline_receipt["source_id"],
            "acquired_at": baseline_receipt["acquired_at"],
            "aoi_id": baseline_receipt["aoi_id"],
            "crs": baseline_receipt["crs"],
            "spatial_resolution_m": baseline_receipt["spatial_resolution_m"],
            "cloud_cover_pct": baseline_receipt["cloud_cover_pct"],
            "valid_pixel_fraction": baseline_receipt["valid_pixel_fraction"],
            "asset_checksums": sorted(baseline_assets),
            "receipt_fingerprint": baseline_receipt["fingerprint"],
        },
        "comparison": {
            "receipt_id": comparison_receipt["receipt_id"],
            "source_id": comparison_receipt["source_id"],
            "acquired_at": comparison_receipt["acquired_at"],
            "aoi_id": comparison_receipt["aoi_id"],
            "crs": comparison_receipt["crs"],
            "spatial_resolution_m": comparison_receipt["spatial_resolution_m"],
            "cloud_cover_pct": comparison_receipt["cloud_cover_pct"],
            "valid_pixel_fraction": comparison_receipt["valid_pixel_fraction"],
            "asset_checksums": sorted(comparison_assets),
            "receipt_fingerprint": comparison_receipt["fingerprint"],
        },
        "processing_notes": processing_notes.strip(),
        "controls": {
            "provider_connection_verified": False,
            "automated_acquisition": False,
            "raster_processing_performed": False,
            "change_analysis_performed": False,
            "human_review_required": True,
            "official_boundary_verified": False,
            "environmental_or_regulatory_conclusion": None,
        },
    }
    payload["fingerprint"] = _digest(payload)
    return payload


def validate_paired_study_manifest(manifest: Any) -> dict[str, Any]:
    """Validate manifest integrity and essential study guardrails."""
    if not isinstance(manifest, Mapping):
        return {"valid": False, "findings": [{"code": "INVALID_MANIFEST_TYPE"}]}
    findings: list[dict[str, str]] = []
    supplied = manifest.get("fingerprint")
    try:
        payload = dict(manifest)
        payload.pop("fingerprint", None)
        if not isinstance(supplied, str) or supplied != _digest(payload):
            findings.append({"code": "MANIFEST_FINGERPRINT_MISMATCH"})
    except (TypeError, ValueError):
        findings.append({"code": "MANIFEST_NOT_CANONICAL_JSON"})
    controls = manifest.get("controls")
    if not isinstance(controls, Mapping):
        findings.append({"code": "CONTROLS_REQUIRED"})
    else:
        for field in ("provider_connection_verified", "automated_acquisition",
                      "raster_processing_performed", "change_analysis_performed",
                      "official_boundary_verified"):
            if controls.get(field) is not False:
                findings.append({"code": f"{field.upper()}_MUST_REMAIN_FALSE"})
        if controls.get("human_review_required") is not True:
            findings.append({"code": "HUMAN_REVIEW_REQUIRED"})
        if controls.get("environmental_or_regulatory_conclusion") is not None:
            findings.append({"code": "CONCLUSION_MUST_REMAIN_UNSET"})
    if manifest.get("study_state") != "READY_FOR_PROCESSING_REVIEW":
        findings.append({"code": "INVALID_STUDY_STATE"})
    return {"valid": not findings, "fingerprint": supplied, "findings": findings}
