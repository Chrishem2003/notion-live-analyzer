from nema_agora.field_eval import scenario_catalog, scenario_fingerprint, evaluate_scenario, summarise_results

def test_catalog_has_six_controlled_scenarios():
    scenarios=scenario_catalog()
    assert len(scenarios)==6
    assert len(scenario_fingerprint(scenarios))==64

def test_complete_scenario_passes():
    scenario=scenario_catalog()[0]
    result=evaluate_scenario(scenario=scenario,observed={"quality_status":"VALID","human_review_required":True})
    assert result.passed

def test_wrong_quality_fails():
    scenario=scenario_catalog()[1]
    result=evaluate_scenario(scenario=scenario,observed={"quality_status":"VALID","human_review_required":True})
    assert not result.passed

def test_summary_is_fail_closed():
    scenario=scenario_catalog()[0]
    result=evaluate_scenario(scenario=scenario,observed={"quality_status":"VALID","human_review_required":True})
    summary=summarise_results([result])
    assert summary["status"]=="PASS"


from nema_agora.field_eval import execute_pipeline


def test_phase21_real_pipeline_execution_has_human_review_contract():
    record = {
        "case_id": "FIELD-PIPE-001", "observation_date": "2026-01-01",
        "category": "Solid waste / illegal dumping", "severity": "Medium",
        "district_or_site": "Synthetic Site",
        "description": "plastic waste near drainage channel", "status": "Received",
        "consent_confirmed": True, "latitude": 1.0, "longitude": 32.0,
    }
    result = execute_pipeline(record=record)
    assert result["analysis"]["human_review_required"] is True
    assert result["reviewer_copilot"]["source_case_id"] == "FIELD-PIPE-001"
