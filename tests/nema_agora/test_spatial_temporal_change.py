from nema_agora.spatial_temporal_change import calculate_change, spatial_temporal_change_evidence, validate_change_inputs

def pair():
    return {"baseline_scene_id":"S2-BASE","comparison_scene_id":"S2-COMP",
            "baseline_acquired_at":"2026-09-01T10:00:00Z","comparison_acquired_at":"2026-10-01T10:00:00Z",
            "baseline_indices":{"NDVI":0.70,"NDWI_MCFEETERS":0.30},
            "comparison_indices":{"NDVI":0.50,"NDWI_MCFEETERS":0.45}}

def test_change_delta_is_transparent():
    assert calculate_change(0.7, 0.5)["delta"] == -0.2
    assert calculate_change(0.7, 0.5)["absolute_delta"] == 0.2

def test_valid_pair_produces_candidate_change_evidence():
    result = spatial_temporal_change_evidence(**pair(), min_temporal_gap_days=7)
    assert result["state"] == "CANDIDATE_CHANGE_EVIDENCE"
    assert result["change"]["NDVI"]["delta"] == -0.2
    assert result["interpretation"]["status"] == "HUMAN_REVIEW_REQUIRED"
    assert result["interpretation"]["environmental_conclusion"] is None

def test_temporal_order_fails_closed():
    data=pair(); data["comparison_acquired_at"]=data["baseline_acquired_at"]
    result=validate_change_inputs(**data)
    assert result["state"]=="CONTROL_REQUIRED"
    assert {"COMPARISON_NOT_AFTER_BASELINE"} <= {x["code"] for x in result["findings"]}

def test_minimum_temporal_gap_is_enforced():
    result=validate_change_inputs(**pair(), min_temporal_gap_days=60)
    assert result["state"]=="CONTROL_REQUIRED"
    assert {"TEMPORAL_GAP_BELOW_MINIMUM"} <= {x["code"] for x in result["findings"]}

def test_missing_index_fails_closed():
    data=pair(); del data["comparison_indices"]["NDWI_MCFEETERS"]
    result=validate_change_inputs(**data)
    assert result["state"]=="CONTROL_REQUIRED"
    assert {"MISSING_COMPARISON_NDWI_MCFEETERS"} <= {x["code"] for x in result["findings"]}

def test_same_scene_is_rejected():
    data=pair(); data["comparison_scene_id"]=data["baseline_scene_id"]
    result=validate_change_inputs(**data)
    assert result["state"]=="CONTROL_REQUIRED"
    assert {"BASELINE_AND_COMPARISON_SCENE_IDENTICAL"} <= {x["code"] for x in result["findings"]}

def test_evidence_is_deterministic_and_non_regulatory():
    first=spatial_temporal_change_evidence(**pair()); second=spatial_temporal_change_evidence(**pair())
    assert first["fingerprint"]==second["fingerprint"]
    assert "violation" not in first
    assert first["interpretation"]["regulatory_conclusion"] is None
