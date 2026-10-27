from nema_agora.impact import make_observation, summarise_impact, dataset_fingerprint

def test_baseline_assisted_metrics_and_delta():
    rows = [
        make_observation(scenario_id="SCN-01", condition="BASELINE", review_seconds=100,
                         evidence_complete=False, duplicate_correct=False, reviewer_actions=5,
                         corrected=True, workflow_success=True),
        make_observation(scenario_id="SCN-01", condition="ASSISTED", review_seconds=60,
                         evidence_complete=True, duplicate_correct=True, reviewer_actions=3,
                         corrected=False, workflow_success=True),
    ]
    summary = summarise_impact(rows)
    assert summary.metrics["delta_assisted_minus_baseline"]["median_review_seconds"] == -40
    assert summary.metrics["delta_assisted_minus_baseline"]["evidence_completeness_rate"] == 1
    assert len(dataset_fingerprint(rows)) == 64

def test_invalid_condition_rejected():
    try:
        make_observation(scenario_id="x", condition="OTHER", review_seconds=1,
                         evidence_complete=True, duplicate_correct=True, reviewer_actions=1,
                         corrected=False, workflow_success=True)
    except ValueError:
        return
    assert False
