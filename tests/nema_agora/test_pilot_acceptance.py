from nema_agora.pilot_acceptance import evaluate_pilot_acceptance
def test_acceptance_rejects_unsafe_boundary():
    good=evaluate_pilot_acceptance(case_count=10,reviewed_count=5,exported_count=2,
        metrics={"execution_gate":"CLOSED","advisory_only":True,"regulatory_truth_claim":False})
    assert good["valid"] and good["official_submission"] is False
    bad=evaluate_pilot_acceptance(case_count=10,reviewed_count=5,exported_count=2,
        metrics={"execution_gate":"OPEN","advisory_only":True,"regulatory_truth_claim":False})
    assert not bad["valid"] and "execution_gate_not_closed" in bad["issues"]
def test_acceptance_rejects_impossible_counts():
    result=evaluate_pilot_acceptance(case_count=2,reviewed_count=3,exported_count=1)
    assert not result["valid"]
