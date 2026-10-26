from copy import deepcopy
import hashlib
import json

from nema_agora.paired_raster_array_analysis import analyze_paired_raster_arrays, validate_paired_array_analysis


def _scene(scene_id, date, *, red, green, nir, mask=None, grid="GRID-001", aoi="AOI-001"):
    shape = len(red), len(red[0])
    return {
        "scene_id": scene_id,
        "acquired_at": f"{date}T10:00:00Z",
        "aoi_id": aoi,
        "grid_id": grid,
        "crs": "EPSG:4326",
        "bands": {"B03": green, "B04": red, "B08": nir},
        "valid_mask": mask or [[True for _ in range(shape[1])] for _ in range(shape[0])],
        "cloud_mask_applied": True,
    }


def _pair():
    baseline = _scene(
        "S2-BASE", "2026-06-01",
        red=[[0.2, 0.2], [0.1, 0.3]],
        green=[[0.4, 0.4], [0.5, 0.3]],
        nir=[[0.6, 0.6], [0.7, 0.5]],
    )
    comparison = _scene(
        "S2-COMP", "2026-09-01",
        red=[[0.3, 0.2], [0.1, 0.4]],
        green=[[0.3, 0.4], [0.6, 0.2]],
        nir=[[0.5, 0.6], [0.7, 0.4]],
    )
    return baseline, comparison


def test_pixelwise_ndvi_ndwi_and_delta_summary_are_calculated():
    baseline, comparison = _pair()
    result = analyze_paired_raster_arrays(
        baseline_scene=baseline, comparison_scene=comparison,
        min_valid_fraction=0.7, min_abs_ndvi_delta=0.1, min_abs_ndwi_delta=0.1,
    )
    assert result["state"] == "PIXEL_ANALYSIS_COMPLETE"
    assert result["grid"]["rows"] == 2
    assert result["quality"]["joint_valid_pixels"] == 4
    assert result["pixel_arrays"]["ndvi_delta"][0][0] < 0
    assert result["pixel_arrays"]["ndwi_delta"][0][0] < 0
    assert result["summary"]["NDVI"]["threshold_hit_pixels"] >= 1
    assert result["interpretation"]["environmental_conclusion"] is None
    assert len(result["fingerprint"]) == 64


def test_masked_pixels_are_not_used_for_comparison():
    baseline, comparison = _pair()
    baseline["valid_mask"] = [[True, False], [True, True]]
    comparison["valid_mask"] = [[True, True], [False, True]]
    result = analyze_paired_raster_arrays(
        baseline_scene=baseline, comparison_scene=comparison,
        min_valid_fraction=0.5,
    )
    assert result["state"] == "PIXEL_ANALYSIS_COMPLETE"
    assert result["quality"]["joint_valid_pixels"] == 2
    assert result["pixel_arrays"]["ndvi_delta"][0][1] is None
    assert result["pixel_arrays"]["ndvi_delta"][1][0] is None


def test_mismatched_grid_and_time_order_fail_closed():
    baseline, comparison = _pair()
    comparison["grid_id"] = "GRID-OTHER"
    result = analyze_paired_raster_arrays(baseline_scene=baseline, comparison_scene=comparison)
    assert result["state"] == "CONTROL_REQUIRED"
    assert {"GRID_ID_MISMATCH"} <= {x["code"] for x in result["findings"]}

    baseline, comparison = _pair()
    baseline["acquired_at"] = "2026-10-01T10:00:00Z"
    result = analyze_paired_raster_arrays(baseline_scene=baseline, comparison_scene=comparison)
    assert {"BASELINE_MUST_PRECEDE_COMPARISON"} <= {x["code"] for x in result["findings"]}


def test_bad_reflectance_shape_or_cloud_mask_fails_closed():
    baseline, comparison = _pair()
    comparison["bands"]["B08"][0][0] = 2.0
    result = analyze_paired_raster_arrays(baseline_scene=baseline, comparison_scene=comparison)
    assert result["state"] == "CONTROL_REQUIRED"
    assert "COMPARISON_INVALID_B08_REFLECTANCE" in {x["code"] for x in result["findings"]}

    baseline, comparison = _pair()
    comparison["cloud_mask_applied"] = False
    result = analyze_paired_raster_arrays(baseline_scene=baseline, comparison_scene=comparison)
    assert "COMPARISON_CLOUD_MASK_REQUIRED" in {x["code"] for x in result["findings"]}


def test_all_zero_denominator_pixels_are_excluded():
    baseline, comparison = _pair()
    for scene in (baseline, comparison):
        scene["bands"]["B03"] = [[0.0, 0.4], [0.5, 0.3]]
        scene["bands"]["B04"] = [[0.0, 0.2], [0.1, 0.3]]
        scene["bands"]["B08"] = [[0.0, 0.6], [0.7, 0.5]]
    result = analyze_paired_raster_arrays(baseline_scene=baseline, comparison_scene=comparison)
    assert result["state"] == "PIXEL_ANALYSIS_COMPLETE"
    assert result["quality"]["joint_valid_pixels"] == 3
    assert result["pixel_arrays"]["ndvi_delta"][0][0] is None


def test_no_comparable_pixels_and_low_quality_are_rejected():
    baseline, comparison = _pair()
    baseline["valid_mask"] = [[True, False], [False, False]]
    comparison["valid_mask"] = [[False, True], [True, True]]
    result = analyze_paired_raster_arrays(
        baseline_scene=baseline, comparison_scene=comparison, min_valid_fraction=0.1
    )
    assert result["state"] == "CONTROL_REQUIRED"
    assert "NO_COMPARABLE_VALID_PIXELS" in {x["code"] for x in result["findings"]}

    baseline, comparison = _pair()
    baseline["valid_mask"] = [[True, False], [True, True]]
    result = analyze_paired_raster_arrays(
        baseline_scene=baseline, comparison_scene=comparison, min_valid_fraction=0.95
    )
    assert "BASELINE_VALID_FRACTION_BELOW_THRESHOLD" in {x["code"] for x in result["findings"]}


def test_fingerprint_is_deterministic_and_output_tampering_is_detectable():
    baseline, comparison = _pair()
    first = analyze_paired_raster_arrays(baseline_scene=baseline, comparison_scene=comparison)
    second = analyze_paired_raster_arrays(baseline_scene=baseline, comparison_scene=comparison)
    assert first["fingerprint"] == second["fingerprint"]
    assert validate_paired_array_analysis(first)["valid"] is True
    tampered = deepcopy(first)
    tampered["pixel_arrays"]["ndvi_delta"][0][0] = 0.9
    assert validate_paired_array_analysis(tampered)["valid"] is False
    assert {"code": "ANALYSIS_FINGERPRINT_MISMATCH"} in validate_paired_array_analysis(tampered)["findings"]


def test_joint_valid_fraction_must_meet_threshold():
    baseline, comparison = _pair()
    baseline["valid_mask"] = [[True, True], [True, False]]
    comparison["valid_mask"] = [[True, False], [False, True]]
    result = analyze_paired_raster_arrays(
        baseline_scene=baseline, comparison_scene=comparison, min_valid_fraction=0.7
    )
    assert result["state"] == "CONTROL_REQUIRED"
    assert "JOINT_VALID_FRACTION_BELOW_THRESHOLD" in {x["code"] for x in result["findings"]}


def test_pixel_limit_and_recomputed_fingerprint_guardrails():
    baseline, comparison = _pair()
    result = analyze_paired_raster_arrays(baseline_scene=baseline, comparison_scene=comparison)
    tampered = deepcopy(result)
    tampered["interpretation"]["environmental_conclusion"] = "confirmed wetland loss"
    payload = dict(tampered)
    payload.pop("fingerprint")
    tampered["fingerprint"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()
    report = validate_paired_array_analysis(tampered)
    assert report["valid"] is False
    assert {"code": "ENVIRONMENTAL_CONCLUSION_MUST_REMAIN_UNSET"} in report["findings"]


def test_invalid_threshold_types_fail_closed_without_exception():
    baseline, comparison = _pair()
    result = analyze_paired_raster_arrays(
        baseline_scene=baseline, comparison_scene=comparison,
        min_valid_fraction="not-a-number",
    )
    assert result["state"] == "CONTROL_REQUIRED"
    assert "INVALID_MIN_VALID_FRACTION" in {x["code"] for x in result["findings"]}
