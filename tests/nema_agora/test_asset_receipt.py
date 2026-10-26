from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest

from nema_agora.asset_receipt import build_manual_asset_receipt, validate_asset_receipt


def _receipt():
    return build_manual_asset_receipt(
        receipt_id="WETLAND-BASELINE-001",
        source_id="COPERNICUS-SENTINEL-2",
        acquired_at="2026-06-15T10:20:00Z",
        recorded_at="2026-10-26T14:00:00+03:00",
        aoi_id="PILOT-AOI-001",
        baseline_or_comparison="baseline",
        crs="EPSG:32636",
        spatial_resolution_m=10,
        cloud_cover_pct=12.5,
        valid_pixel_fraction=0.91,
        assets=[{
            "asset_id": "SCENE-BANDS-001",
            "sha256": hashlib.sha256(b"test-asset-not-real-imagery").hexdigest(),
            "storage_ref": "upload://pilot/scene-bands-001",
            "media_type": "image/tiff",
        }],
        limitations=[
            "Fixture metadata only; this test asset is not satellite imagery.",
            "Source authenticity and licence require separate verification.",
        ],
    )


def test_manual_receipt_is_reproducible_and_explicitly_not_live():
    receipt = _receipt()
    report = validate_asset_receipt(receipt)
    assert report["valid"] is True
    assert len(receipt["fingerprint"]) == 64
    assert receipt["acquisition_method"] == "manual_upload"
    assert receipt["provider_connection_verified"] is False
    assert receipt["automated_acquisition"] is False
    assert _receipt()["fingerprint"] == receipt["fingerprint"]


def test_receipt_rejects_tampering_and_bad_checksum():
    receipt = deepcopy(_receipt())
    receipt["assets"][0]["sha256"] = "not-a-sha256"
    report = validate_asset_receipt(receipt)
    assert report["valid"] is False
    assert {"code": "ASSET_0_INVALID_SHA256"} in report["findings"]
    assert {"code": "RECEIPT_FINGERPRINT_MISMATCH"} in report["findings"]


def test_receipt_rejects_missing_provenance_and_bad_quality_metadata():
    receipt = deepcopy(_receipt())
    receipt["source_id"] = "UNKNOWN-SOURCE"
    receipt["acquired_at"] = "yesterday"
    receipt["cloud_cover_pct"] = 101
    receipt["valid_pixel_fraction"] = -0.1
    receipt.pop("fingerprint")
    receipt["fingerprint"] = "0" * 64
    report = validate_asset_receipt(receipt)
    codes = {item["code"] for item in report["findings"]}
    assert {"UNKNOWN_SOURCE_ID", "INVALID_ACQUIRED_AT_TIMESTAMP",
            "INVALID_CLOUD_COVER", "INVALID_VALID_PIXEL_FRACTION"} <= codes


def test_receipt_fails_closed_on_unverified_live_provider_claims():
    receipt = deepcopy(_receipt())
    receipt["provider_connection_verified"] = True
    receipt["automated_acquisition"] = True
    report = validate_asset_receipt(receipt)
    codes = {item["code"] for item in report["findings"]}
    assert "UNVERIFIED_PROVIDER_CONNECTION_CLAIM" in codes
    assert "UNVERIFIED_AUTOMATED_ACQUISITION_CLAIM" in codes


def test_provider_api_receipt_is_blocked_until_adapter_verification_exists():
    receipt = deepcopy(_receipt())
    receipt["acquisition_method"] = "provider_api"
    report = validate_asset_receipt(receipt)
    assert report["valid"] is False
    assert {"code": "PROVIDER_API_RECEIPT_REQUIRES_SEPARATE_VERIFICATION"} in report["findings"]


def test_builder_rejects_invalid_receipt_instead_of_saving_it():
    with pytest.raises(ValueError, match="UNKNOWN_SOURCE_ID"):
        build_manual_asset_receipt(
            receipt_id="BAD-RECEIPT",
            source_id="NOT-REGISTERED",
            acquired_at="2026-06-15T10:20:00Z",
            recorded_at="2026-10-26T14:00:00Z",
            aoi_id="PILOT-AOI-001",
            baseline_or_comparison="baseline",
            crs="EPSG:32636",
            spatial_resolution_m=10,
            cloud_cover_pct=10,
            valid_pixel_fraction=0.9,
            assets=[{
                "asset_id": "ASSET-1",
                "sha256": hashlib.sha256(b"x").hexdigest(),
                "storage_ref": "upload://asset-1",
                "media_type": "image/tiff",
            }],
            limitations=["Unverified source."],
        )
