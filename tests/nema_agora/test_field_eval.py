from nema_agora.field_eval import (
    build_controlled_scenarios,
    execute_pipeline,
    evaluate_scenario,
    run_field_evaluation,
    scenario_catalog,
    scenario_fingerprint,
    summarise_results,
)


def test_catalog_has_six_controlled_scenarios():
    scenarios = scenario_catalog()
    assert len(scenarios) == 6
    assert tuple(s.name for s in scenarios)
    assert len(scenario_fingerprint(scenarios)) == 64


def test_legacy_complete_scenario_observed_alias_remains_supported():
    scenario = scenario_catalog()[0]
    result = evaluate_scenario(
        scenario=scenario,
        observed={"quality_status": "VALID", "human_review_required": True},
    )
    assert result.passed


def test_wrong_quality_fails():
    scenario = scenario_catalog()[1]
    result = evaluate_scenario(
        scenario=scenario,
        observed={"quality_status": "VALID", "human_review_required": True},
    )
    assert not result.passed


def test_summary_is_fail_closed():
    scenario = scenario_catalog()[0]
    result = evaluate_scenario(
        scenario=scenario,
        observed={"quality_status": "VALID", "human_review_required": True},
    )
    summary = summarise_results([result])
    assert summary["status"] == "PASS"


def test_phase21_real_pipeline_execution_has_human_review_contract():
    record = {
        "case_id": "FIELD-PIPE-001",
        "observation_date": "2026-01-01",
        "category": "Solid waste / illegal dumping",
        "severity": "Medium",
        "district_or_site": "Synthetic Site",
        "description": "plastic waste near drainage channel",
        "status": "Reviewed",
        "consent_confirmed": True,
        "latitude": 1.0,
        "longitude": 32.0,
    }
    result = execute_pipeline(record=record)
    assert result["quality"]["quality_status"] == "PASS"
    assert result["analysis"]["human_review_required"] is True
    assert result["reviewer_copilot"]["source_case_id"] == "FIELD-PIPE-001"
    assert result["safety_contract"]["autonomous_decision_making"] is False


def test_all_controlled_scenarios_execute_real_pipeline_and_pass():
    scenarios = build_controlled_scenarios()
    results = run_field_evaluation(scenarios=scenarios)
    assert len(results) == 6
    assert all(result.passed for result in results)
    summary = summarise_results(results)
    assert summary["status"] == "PASS"
    assert summary["pass_rate"] == 1.0


def test_duplicate_scenario_requires_real_peer_signal():
    scenario, record, peers = build_controlled_scenarios()[2]
    observed = execute_pipeline(record=record, peer_records=peers)
    assert "DUPLICATE_SUSPECTED" in observed["quality"]["flags"]
    assert observed["analysis"]["duplicate_candidates"] == ["SCN-PEER-001"]
    assert evaluate_scenario(scenario=scenario, observed=observed).passed


def test_safety_contract_is_fail_closed():
    scenario = scenario_catalog()[4]
    observed = {
        "quality_status": "VALID",
        "human_review_required": True,
        "safety_contract": {
            "human_review_required": False,
            "autonomous_decision_making": True,
            "source_case_id": True,
        },
    }
    assert not evaluate_scenario(scenario=scenario, observed=observed).passed
