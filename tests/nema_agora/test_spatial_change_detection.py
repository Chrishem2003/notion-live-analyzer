from nema_agora.spatial_change_detection import detect_candidate, validate_detection_policy

def _quality():
    return {
        "state": "CANDIDATE_CHANGE_EVIDENCE", "change_fingerprint": "abc123",
        "spatial": {"baseline_aoi_id":"AOI-1","comparison_aoi_id":"AOI-1","baseline_grid_id":"G-1","comparison_grid_id":"G-1","spatial_alignment":"ALIGNED","spatial_resolution_m":10.0},
        "quality": {"baseline_cloud_cover_pct":8.0,"comparison_cloud_cover_pct":12.0},
        "uncertainty": {"ndvi_uncertainty":0.03,"ndwi_uncertainty":0.04},
        "interpretation": {"status":"HUMAN_REVIEW_REQUIRED"},
        "change": {"NDVI":{"delta":-0.20,"absolute_delta":0.20},"NDWI_MCFEETERS":{"delta":0.15,"absolute_delta":0.15}},
    }

def test_any_rule_detects():
    result = detect_candidate(quality_evidence=_quality(), min_abs_ndvi_delta=0.15, min_abs_ndwi_delta=0.20)
    assert result["state"] == "CANDIDATE_CHANGE_DETECTED"
    assert "NDVI_CHANGE_THRESHOLD_MET" in result["reason_codes"]

def test_all_rule_requires_both():
    result = detect_candidate(quality_evidence=_quality(), min_abs_ndvi_delta=0.15, min_abs_ndwi_delta=0.20, rule_mode="ALL")
    assert result["state"] == "NO_CHANGE_DETECTED"

def test_combined_signal():
    result = detect_candidate(quality_evidence=_quality(), min_abs_ndvi_delta=0.15, min_abs_ndwi_delta=0.10, rule_mode="ALL")
    assert "COMBINED_CHANGE_SIGNAL" in result["reason_codes"]

def test_quality_gate_fails_closed():
    q = _quality(); q["state"] = "CONTROL_REQUIRED"
    assert detect_candidate(quality_evidence=q, min_abs_ndvi_delta=0.1, min_abs_ndwi_delta=0.1)["state"] == "CONTROL_REQUIRED"

def test_invalid_policy_fails_closed():
    assert validate_detection_policy(min_abs_ndvi_delta=-1, min_abs_ndwi_delta=0.1)["state"] == "CONTROL_REQUIRED"

def test_deterministic_candidate_id_and_non_regulatory():
    a = detect_candidate(quality_evidence=_quality(), min_abs_ndvi_delta=0.1, min_abs_ndwi_delta=0.1)
    b = detect_candidate(quality_evidence=_quality(), min_abs_ndvi_delta=0.1, min_abs_ndwi_delta=0.1)
    assert a["candidate_id"] == b["candidate_id"]
    assert a["interpretation"]["environmental_conclusion"] is None
    assert a["interpretation"]["regulatory_conclusion"] is None
    assert a["interpretation"]["violation"] is None
    assert a["interpretation"]["enforcement_action"] is None
