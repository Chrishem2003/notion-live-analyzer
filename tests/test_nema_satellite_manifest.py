"""Tests for satellite evaluation dataset-manifest controls."""
import pytest
from nema_agora.satellite_manifest import SatelliteManifestError, validate_dataset_manifest


def valid_manifest(**overrides):
    data = {
        "dataset_id": "wetland-pilot-2026", "aoi_id": "AOI-NORTH-01",
        "sensor": "Sentinel-2", "product_id": "L2A", "processing_version": "processor-v1",
        "crs": "EPSG:32636", "grid_id": "grid-10m-v1",
        "reference_set_id": "ref-set-01", "reference_set_version": "v1",
        "sampling_method": "stratified-random", "label_review_method": "two-reviewer-adjudication",
        "candidate_policy_version": "candidate-v1", "split": "holdout",
        "acquisition_start": "2026-01-01", "acquisition_end": "2026-01-31",
        "cloud_filter_method": "provider-mask-plus-scene-filter",
        "valid_pixel_method": "valid-pixel-count-over-aoi",
        "spatial_resolution_m": 10.0, "cloud_cover_pct": 12.0,
        "valid_pixel_fraction": 0.82, "source_sha256": "a" * 64,
    }
    data.update(overrides)
    return data


def test_valid_manifest_has_stable_digest_and_explicit_nonverified_state():
    data = valid_manifest()
    first = validate_dataset_manifest(data)
    second = validate_dataset_manifest(data)
    assert first["state"] == "METADATA_COMPLETE_NOT_INDEPENDENTLY_VERIFIED"
    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert len(first["manifest_sha256"]) == 64
    assert first["manifest"]["schema_version"] == "satellite-dataset-manifest-v1"


@pytest.mark.parametrize("overrides", [
    {"acquisition_end": "2025-12-31"}, {"split": "final"},
    {"spatial_resolution_m": 0}, {"cloud_cover_pct": 101},
    {"valid_pixel_fraction": -0.1}, {"source_sha256": "not-a-hash"},
    {"aoi_id": "bad id with spaces"}, {"sampling_method": ""},
])
def test_inconsistent_or_invalid_metadata_is_rejected(overrides):
    with pytest.raises(SatelliteManifestError):
        validate_dataset_manifest(valid_manifest(**overrides))


def test_missing_quality_metadata_is_rejected():
    data = valid_manifest()
    del data["cloud_cover_pct"]
    with pytest.raises(SatelliteManifestError, match="cloud_cover_pct"):
        validate_dataset_manifest(data)


def test_manifest_does_not_claim_holdout_independence():
    result = validate_dataset_manifest(valid_manifest(split="holdout"))
    assert any("not proof" in warning for warning in result["warnings"])
