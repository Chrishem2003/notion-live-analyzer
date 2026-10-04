from nema_agora.impact import make_observation
from nema_agora.outcomes import build_outcome_study, validate_outcome_study

def _obs(scenario, condition, seconds, complete, duplicate, actions, corrected, success):
    return make_observation(
        scenario_id=scenario, condition=condition, review_seconds=seconds,
        evidence_complete=complete, duplicate_correct=duplicate,
        reviewer_actions=actions, corrected=corrected, workflow_success=success,
    )

def test_outcome_study_pairs_matching_scenarios():
    observations=[
        _obs("S1","BASELINE",100,False,False,5,True,False),
        _obs("S1","ASSISTED",60,True,True,3,False,True),
    ]
    study=build_outcome_study(observations)
    assert study.sample_size==1
    assert study.metrics["time_to_review_delta_assisted_minus_baseline"]==-40.0
    assert study.metrics["evidence_completeness_delta"]==1.0
    assert validate_outcome_study(study,observations)["valid"] is True

def test_outcome_study_ignores_unmatched_conditions():
    observations=[_obs("S1","BASELINE",100,True,True,4,False,True)]
    study=build_outcome_study(observations)
    assert study.sample_size==0
    assert validate_outcome_study(study,observations)["valid"] is True


def test_outcome_study_fingerprint_is_stable_for_same_observations():
    observations=[
        _obs("S1","BASELINE",100,True,False,4,False,True),
        _obs("S1","ASSISTED",80,True,True,3,False,True),
    ]
    first=build_outcome_study(observations)
    second=build_outcome_study(observations)
    assert first.dataset_fingerprint==second.dataset_fingerprint
    assert first.pairs[0].pair_id==second.pairs[0].pair_id
    assert first.study_id==second.study_id

def test_outcome_validation_detects_missing_paired_observation():
    observations=[
        _obs("S1","BASELINE",100,True,True,4,False,True),
        _obs("S1","ASSISTED",80,True,True,3,False,True),
    ]
    study=build_outcome_study(observations)
    reduced=[observations[0]]
    result=validate_outcome_study(study,reduced)
    assert result["valid"] is False
    assert any(error.startswith("MISSING_OBSERVATION") for error in result["errors"])
