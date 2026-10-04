from nema_agora.spatial_change_scoring import score_candidate,validate_scoring_policy
def _candidate():
    return {"state":"CANDIDATE_CHANGE_DETECTED","candidate_id":"CHANGE-1","fingerprint":"FP-1","spatial":{"spatial_alignment":"ALIGNED"},"change":{"NDVI":{"absolute_delta":0.2},"NDWI_MCFEETERS":{"absolute_delta":0.15}},"quality":{"baseline_cloud_cover_pct":8,"comparison_cloud_cover_pct":12,"baseline_valid_fraction":0.94,"comparison_valid_fraction":0.91},"uncertainty":{"ndvi_uncertainty":0.03,"ndwi_uncertainty":0.04},"reason_codes":["COMBINED_CHANGE_SIGNAL"]}
def test_score_assigned(): assert score_candidate(candidate=_candidate())["state"]=="REVIEW_PRIORITY_ASSIGNED"
def test_bad_candidate_fails_closed(): assert score_candidate(candidate={})["state"]=="CONTROL_REQUIRED"
def test_bad_policy_fails_closed(): assert validate_scoring_policy(ndvi_weight=-1)["state"]=="CONTROL_REQUIRED"
def test_deterministic_and_safe():
    a=score_candidate(candidate=_candidate());b=score_candidate(candidate=_candidate())
    assert a["fingerprint"]==b["fingerprint"];assert a["interpretation"]["environmental_conclusion"] is None;assert a["interpretation"]["violation"] is None
def test_priority_changes_with_threshold():
    a=score_candidate(candidate=_candidate(),review_threshold=0.99)
    assert a["interpretation"]["status"]=="LOWER_PRIORITY_REVIEW"
