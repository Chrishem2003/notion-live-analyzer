from copy import deepcopy

from nema_agora.scene_comparability import assess_scene_comparability


def _scene(scene_id, date):
    return {
        "scene_id": scene_id,
        "acquired_at": f"{date}T10:00:00Z",
        "aoi_id": "AOI-001",
        "grid_id": "GRID-001",
        "crs": "EPSG:4326",
        "domain_mask": [[True, True], [True, True]],
        "valid_mask": [[True, True], [True, True]],
        "ingestion": {
            "reflectance_scale": 0.0001,
            "reflectance_offset": 0.0,
            "band_mapping": {"B03": 1, "B04": 2, "B08": 3},
            "band_mapping_confirmed_by_uploader": True,
            "cloud_shadow_mask_applied_by_uploader": True,
            "aoi_valid_pixel_fraction": 0.95,
            "aoi_sha256": "a" * 64,
            "aoi_clipping_applied": True,
            "raster_sha256": "b" * 64,
            "valid_mask_sha256": "c" * 64,
            "raster_driver": "GTiff",
        },
    }


def test_comparable_pair_passes_screening_checks():
    report = assess_scene_comparability(_scene("BASE", "2026-06-01"), _scene("COMP", "2026-06-20"))
    assert report["state"] == "COMPARABILITY_CHECKS_PASSED"
    assert report["blocking_findings"] == []
    assert report["thresholds"]["thresholds_are_screening_defaults"] is True


def test_grid_aoi_domain_and_scaling_mismatches_block():
    baseline, comparison = _scene("BASE", "2026-06-01"), _scene("COMP", "2026-06-20")
    comparison["grid_id"] = "GRID-OTHER"
    comparison["aoi_id"] = "AOI-OTHER"
    comparison["domain_mask"] = [[True, False], [True, True]]
    comparison["ingestion"]["reflectance_scale"] = 0.001
    report = assess_scene_comparability(baseline, comparison)
    codes = {item["code"] for item in report["blocking_findings"]}
    assert {"GRID_ID_MISMATCH", "AOI_ID_MISMATCH", "AOI_DOMAIN_MASK_MISMATCH", "REFLECTANCE_SCALING_MISMATCH"} <= codes
    assert report["state"] == "CONTROL_REQUIRED"


def test_long_interval_and_seasonal_gap_are_warnings_not_proof():
    baseline = _scene("BASE", "2026-01-10")
    comparison = _scene("COMP", "2026-09-20")
    report = assess_scene_comparability(baseline, comparison, max_interval_days=120, max_day_of_year_gap=30)
    codes = {item["code"] for item in report["warnings"]}
    assert "SCENE_INTERVAL_EXCEEDS_REVIEW_THRESHOLD" in codes
    assert "SEASONAL_WINDOW_DIFFERENCE_REQUIRES_REVIEW" in codes
    assert report["state"] == "REVIEW_WARNINGS"
    assert "do not establish scientific comparability" in report["review_boundary"]


def test_bad_time_order_and_unconfirmed_mask_block():
    baseline, comparison = _scene("BASE", "2026-08-01"), _scene("COMP", "2026-06-20")
    comparison["ingestion"]["cloud_shadow_mask_applied_by_uploader"] = False
    report = assess_scene_comparability(baseline, comparison)
    codes = {item["code"] for item in report["blocking_findings"]}
    assert "BASELINE_MUST_PRECEDE_COMPARISON" in codes
    assert "COMPARISON_CLOUD_MASK_NOT_CONFIRMED" in codes


def test_low_coverage_and_invalid_thresholds_fail_closed():
    baseline, comparison = _scene("BASE", "2026-06-01"), _scene("COMP", "2026-06-20")
    baseline["ingestion"]["aoi_valid_pixel_fraction"] = 0.2
    report = assess_scene_comparability(baseline, comparison, min_valid_fraction=0.7)
    assert "BASELINE_VALID_PIXEL_FRACTION_BELOW_THRESHOLD" in {item["code"] for item in report["blocking_findings"]}
    bad = assess_scene_comparability(baseline, comparison, max_interval_days=0)
    assert "INVALID_MAX_INTERVAL_DAYS" in {item["code"] for item in bad["blocking_findings"]}


def test_missing_ingestion_provenance_blocks():
    baseline, comparison = _scene("BASE", "2026-06-01"), _scene("COMP", "2026-06-20")
    del comparison["ingestion"]
    report = assess_scene_comparability(baseline, comparison)
    assert "COMPARISON_MISSING_INGESTION" in {item["code"] for item in report["blocking_findings"]}



def test_aoi_geometry_fingerprint_mismatch_blocks_even_if_domain_masks_match():
    baseline, comparison = _scene("BASE", "2026-06-01"), _scene("COMP", "2026-06-20")
    comparison["ingestion"]["aoi_sha256"] = "d" * 64
    report = assess_scene_comparability(baseline, comparison)
    assert "AOI_GEOMETRY_FINGERPRINT_MISMATCH" in {
        item["code"] for item in report["blocking_findings"]
    }
