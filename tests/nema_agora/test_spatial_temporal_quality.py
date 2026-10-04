from nema_agora.spatial_temporal_change import spatial_temporal_change_evidence
from nema_agora.spatial_temporal_quality import validate_change_quality, spatial_temporal_quality_evidence

def quality():
    change = spatial_temporal_change_evidence(
        baseline_scene_id="S2-BASE", comparison_scene_id="S2-COMP",
        baseline_acquired_at="2026-09-01T10:00:00Z", comparison_acquired_at="2026-10-01T10:00:00Z",
        baseline_indices={"NDVI": 0.70, "NDWI_MCFEETERS": 0.30},
        comparison_indices={"NDVI": 0.50, "NDWI_MCFEETERS": 0.45})
    return dict(change_evidence=change, baseline_aoi_id="AOI-001", comparison_aoi_id="AOI-001",
        baseline_grid_id="GRID-001", comparison_grid_id="GRID-001", spatial_alignment="ALIGNED",
        spatial_resolution_m=10.0, baseline_cloud_cover_pct=10.0, comparison_cloud_cover_pct=12.0,
        baseline_valid_fraction=0.92, comparison_valid_fraction=0.88, ndvi_uncertainty=0.03, ndwi_uncertainty=0.04)

def qonly(data):
    return {k: v for k, v in data.items() if k != "change_evidence"}

def test_valid_quality_is_accepted_for_review():
    result = spatial_temporal_quality_evidence(**quality())
    assert result["state"] == "CANDIDATE_CHANGE_EVIDENCE"
    assert result["interpretation"]["evidence_quality"] == "ACCEPTED_FOR_REVIEW"

def test_aoi_mismatch_fails_closed():
    data = quality(); data["comparison_aoi_id"] = "AOI-002"
    result = validate_change_quality(**qonly(data))
    assert result["state"] == "CONTROL_REQUIRED"
    assert "AOI_ID_MISMATCH" in {x["code"] for x in result["findings"]}

def test_grid_mismatch_fails_closed():
    data = quality(); data["comparison_grid_id"] = "GRID-002"
    assert validate_change_quality(**qonly(data))["state"] == "CONTROL_REQUIRED"

def test_unverified_alignment_fails_closed():
    data = quality(); data["spatial_alignment"] = "UNVERIFIED"
    result = validate_change_quality(**qonly(data))
    assert result["state"] == "CONTROL_REQUIRED"
    assert "SPATIAL_ALIGNMENT_UNVERIFIED" in {x["code"] for x in result["findings"]}

def test_quality_thresholds_fail_closed():
    data = quality(); data["baseline_cloud_cover_pct"] = 45.0; data["comparison_valid_fraction"] = 0.40
    codes = {x["code"] for x in validate_change_quality(**qonly(data))["findings"]}
    assert "BASELINE_CLOUD_COVER_ABOVE_THRESHOLD" in codes
    assert "COMPARISON_VALID_FRACTION_BELOW_THRESHOLD" in codes

def test_uncertainty_must_be_nonnegative_finite():
    data = quality(); data["ndvi_uncertainty"] = -0.1
    assert validate_change_quality(**qonly(data))["state"] == "CONTROL_REQUIRED"

def test_quality_evidence_is_deterministic_and_non_regulatory():
    first = spatial_temporal_quality_evidence(**quality())
    second = spatial_temporal_quality_evidence(**quality())
    assert first["fingerprint"] == second["fingerprint"]
    assert "violation" not in first
    assert first["interpretation"]["regulatory_conclusion"] is None
