"""Reproducible receipt for manually supplied or verified environmental assets.

This module records provenance and quality metadata; it does not download imagery,
connect to providers, or infer that an asset is authentic from its filename.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from typing import Any, Mapping

from nema_agora.source_registry import SOURCES

POLICY_VERSION = "asset-receipt-v1"
_SOURCE_IDS = {item["source_id"] for item in SOURCES}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _digest(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_asset_receipt(receipt: Any) -> dict[str, Any]:
    """Validate required provenance, metadata and honest connection status."""
    findings: list[dict[str, str]] = []
    if not isinstance(receipt, Mapping):
        return {"policy_version": POLICY_VERSION, "valid": False,
                "findings": [{"code": "INVALID_RECEIPT_TYPE"}]}
    required = (
        "receipt_id", "source_id", "acquisition_method", "acquired_at",
        "recorded_at", "aoi_id", "baseline_or_comparison", "crs",
        "spatial_resolution_m", "cloud_cover_pct", "valid_pixel_fraction",
        "assets", "provider_connection_verified", "automated_acquisition",
        "limitations", "fingerprint",
    )
    for field in required:
        if field not in receipt:
            findings.append({"code": f"MISSING_{field.upper()}"})
    if findings:
        return {"policy_version": POLICY_VERSION, "valid": False, "findings": findings}

    if not isinstance(receipt.get("receipt_id"), str) or not _ID.fullmatch(receipt["receipt_id"]):
        findings.append({"code": "INVALID_RECEIPT_ID"})
    if receipt.get("source_id") not in _SOURCE_IDS:
        findings.append({"code": "UNKNOWN_SOURCE_ID"})
    if receipt.get("acquisition_method") not in {"manual_upload", "provider_api"}:
        findings.append({"code": "INVALID_ACQUISITION_METHOD"})
    for field in ("acquired_at", "recorded_at"):
        if not _utc_timestamp(receipt.get(field)):
            findings.append({"code": f"INVALID_{field.upper()}_TIMESTAMP"})
    if not isinstance(receipt.get("aoi_id"), str) or not _ID.fullmatch(receipt["aoi_id"]):
        findings.append({"code": "INVALID_AOI_ID"})
    if receipt.get("baseline_or_comparison") not in {"baseline", "comparison", "context"}:
        findings.append({"code": "INVALID_ASSET_ROLE"})
    if not isinstance(receipt.get("crs"), str) or not receipt["crs"].strip():
        findings.append({"code": "MISSING_CRS"})
    resolution = receipt.get("spatial_resolution_m")
    if not _finite_number(resolution) or float(resolution) <= 0:
        findings.append({"code": "INVALID_SPATIAL_RESOLUTION"})
    cloud = receipt.get("cloud_cover_pct")
    if not _finite_number(cloud) or not 0 <= float(cloud) <= 100:
        findings.append({"code": "INVALID_CLOUD_COVER"})
    valid_fraction = receipt.get("valid_pixel_fraction")
    if not _finite_number(valid_fraction) or not 0 <= float(valid_fraction) <= 1:
        findings.append({"code": "INVALID_VALID_PIXEL_FRACTION"})

    assets = receipt.get("assets")
    if not isinstance(assets, list) or not assets:
        findings.append({"code": "ASSET_LIST_REQUIRED"})
    else:
        seen: set[str] = set()
        for i, asset in enumerate(assets):
            prefix = f"ASSET_{i}"
            if not isinstance(asset, Mapping):
                findings.append({"code": f"{prefix}_INVALID"})
                continue
            asset_id = asset.get("asset_id")
            if not isinstance(asset_id, str) or not _ID.fullmatch(asset_id):
                findings.append({"code": f"{prefix}_INVALID_ID"})
            elif asset_id in seen:
                findings.append({"code": f"{prefix}_DUPLICATE_ID"})
            else:
                seen.add(asset_id)
            if not isinstance(asset.get("sha256"), str) or not _SHA256.fullmatch(asset["sha256"]):
                findings.append({"code": f"{prefix}_INVALID_SHA256"})
            if not isinstance(asset.get("storage_ref"), str) or not asset["storage_ref"].strip():
                findings.append({"code": f"{prefix}_MISSING_STORAGE_REF"})
            if not isinstance(asset.get("media_type"), str) or not asset["media_type"].strip():
                findings.append({"code": f"{prefix}_MISSING_MEDIA_TYPE"})

    if receipt.get("provider_connection_verified") is not False:
        findings.append({"code": "UNVERIFIED_PROVIDER_CONNECTION_CLAIM"})
    if receipt.get("automated_acquisition") is not False:
        findings.append({"code": "UNVERIFIED_AUTOMATED_ACQUISITION_CLAIM"})
    if receipt.get("acquisition_method") == "provider_api":
        findings.append({"code": "PROVIDER_API_RECEIPT_REQUIRES_SEPARATE_VERIFICATION"})
    if not isinstance(receipt.get("limitations"), list) or not receipt["limitations"]:
        findings.append({"code": "LIMITATIONS_REQUIRED"})

    try:
        payload = dict(receipt)
        supplied = payload.pop("fingerprint")
        if not isinstance(supplied, str) or supplied != _digest(payload):
            findings.append({"code": "RECEIPT_FINGERPRINT_MISMATCH"})
    except (TypeError, ValueError):
        findings.append({"code": "RECEIPT_NOT_CANONICAL_JSON"})
    return {
        "policy_version": POLICY_VERSION,
        "valid": not findings,
        "receipt_id": receipt.get("receipt_id"),
        "fingerprint": receipt.get("fingerprint"),
        "findings": findings,
    }


def build_manual_asset_receipt(
    *,
    receipt_id: str,
    source_id: str,
    acquired_at: str,
    recorded_at: str,
    aoi_id: str,
    baseline_or_comparison: str,
    crs: str,
    spatial_resolution_m: float,
    cloud_cover_pct: float,
    valid_pixel_fraction: float,
    assets: list[Mapping[str, Any]],
    limitations: list[str],
) -> dict[str, Any]:
    """Create a sealed receipt for assets supplied by a user, never a live feed."""
    receipt: dict[str, Any] = {
        "policy_version": POLICY_VERSION,
        "receipt_id": receipt_id,
        "source_id": source_id,
        "acquisition_method": "manual_upload",
        "acquired_at": acquired_at,
        "recorded_at": recorded_at,
        "aoi_id": aoi_id,
        "baseline_or_comparison": baseline_or_comparison,
        "crs": crs,
        "spatial_resolution_m": spatial_resolution_m,
        "cloud_cover_pct": cloud_cover_pct,
        "valid_pixel_fraction": valid_pixel_fraction,
        "assets": [dict(item) for item in assets],
        "provider_connection_verified": False,
        "automated_acquisition": False,
        "limitations": list(limitations),
    }
    receipt["fingerprint"] = _digest(receipt)
    report = validate_asset_receipt(receipt)
    if not report["valid"]:
        codes = ", ".join(item["code"] for item in report["findings"])
        raise ValueError(f"Asset receipt validation failed: {codes}")
    return receipt
