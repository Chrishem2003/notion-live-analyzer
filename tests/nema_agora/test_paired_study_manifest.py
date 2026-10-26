from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest

from nema_agora.asset_receipt import build_manual_asset_receipt
from nema_agora.paired_study_manifest import (
    build_paired_study_manifest,
    validate_paired_study_manifest,
)


def _aoi():
    return {
        "type": "Feature",
        "properties": {"label": "synthetic test AOI"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [32.50, 0.30], [32.51, 0.30], [32.51, 0.31],
                [32.50, 0.31], [32.50, 0.30],
            ]],
        },
    }


def _receipt(role, day, payload):
    return build_manual_asset_receipt(
        receipt_id=f"STUDY-{role.upper()}-001",
        source_id="COPERNICUS-SENTINEL-2",
        acquired_at=f"{day}T10:00:00Z",
        recorded_at="2026-10-26T14:00:00+03:00",
        aoi_id="PILOT-AOI-001",
        baseline_or_comparison=role,
        crs="EPSG:32636",
        spatial_resolution_m=10,
        cloud_cover_pct=8.0,
        valid_pixel_fraction=0.93,
        assets=[{
            "asset_id": f"ASSET-{role.upper()}-001",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "storage_ref": f"session-upload://{role}/scene.tif",
            "media_type": "image/tiff",
        }],
        limitations=["Synthetic fixture metadata only; not real satellite imagery."],
    )


def _manifest():
    baseline = _receipt("baseline", "2026-06-01", b"baseline-fixture")
    comparison = _receipt("comparison", "2026-09-01", b"comparison-fixture")
    return build_paired_study_manifest(
        study_id="WETLAND-PILOT-001",
        aoi_document=_aoi(),
        baseline_receipt=baseline,
        comparison_receipt=comparison,
        processing_notes="Confirm acquisition metadata, cloud masks, grid alignment, and seasonality before processing.",
    )


def test_builds_fingerprinted_paired_scene_manifest():
    manifest = _manifest()
    report = validate_paired_study_manifest(manifest)
    assert report["valid"] is True
    assert manifest["study_state"] == "READY_FOR_PROCESSING_REVIEW"
    assert manifest["aoi"]["bounds"]["west"] == 32.5
    assert manifest["baseline"]["acquired_at"] < manifest["comparison"]["acquired_at"]
    assert manifest["controls"]["raster_processing_performed"] is False
    assert manifest["controls"]["change_analysis_performed"] is False
    assert manifest["controls"]["human_review_required"] is True
    assert _manifest()["fingerprint"] == manifest["fingerprint"]


def test_rejects_receipt_role_or_comparison_metadata_mismatch():
    baseline = _receipt("baseline", "2026-06-01", b"baseline-fixture")
    comparison = _receipt("comparison", "2026-09-01", b"comparison-fixture")
    comparison["crs"] = "EPSG:4326"
    with pytest.raises(ValueError, match="CRS_MISMATCH"):
        build_paired_study_manifest(
            study_id="WETLAND-PILOT-001",
            aoi_document=_aoi(),
            baseline_receipt=baseline,
            comparison_receipt=comparison,
            processing_notes="Check scene comparability.",
        )


def test_rejects_baseline_after_comparison_and_missing_notes():
    baseline = _receipt("baseline", "2026-09-01", b"baseline-fixture")
    comparison = _receipt("comparison", "2026-06-01", b"comparison-fixture")
    with pytest.raises(ValueError, match="BASELINE_MUST_PRECEDE_COMPARISON"):
        build_paired_study_manifest(
            study_id="WETLAND-PILOT-001", aoi_document=_aoi(),
            baseline_receipt=baseline, comparison_receipt=comparison,
            processing_notes="Temporal order check.",
        )
    baseline = _receipt("baseline", "2026-06-01", b"baseline-fixture")
    comparison = _receipt("comparison", "2026-09-01", b"comparison-fixture")
    with pytest.raises(ValueError, match="PROCESSING_NOTES_REQUIRED"):
        build_paired_study_manifest(
            study_id="WETLAND-PILOT-001", aoi_document=_aoi(),
            baseline_receipt=baseline, comparison_receipt=comparison,
            processing_notes=" ",
        )


def test_rejects_same_asset_bytes_reused_as_both_scenes():
    baseline = _receipt("baseline", "2026-06-01", b"same-bytes")
    comparison = _receipt("comparison", "2026-09-01", b"same-bytes")
    with pytest.raises(ValueError, match="BASELINE_AND_COMPARISON_ASSETS_OVERLAP"):
        build_paired_study_manifest(
            study_id="WETLAND-PILOT-001", aoi_document=_aoi(),
            baseline_receipt=baseline, comparison_receipt=comparison,
            processing_notes="Check distinct source scene assets.",
        )


def test_manifest_fails_closed_on_tampering_and_claims():
    manifest = deepcopy(_manifest())
    manifest["controls"]["automated_acquisition"] = True
    report = validate_paired_study_manifest(manifest)
    codes = {item["code"] for item in report["findings"]}
    assert "AUTOMATED_ACQUISITION_MUST_REMAIN_FALSE" in codes
    assert "MANIFEST_FINGERPRINT_MISMATCH" in codes
