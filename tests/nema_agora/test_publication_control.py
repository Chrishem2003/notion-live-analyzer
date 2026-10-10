from nema_agora.publication_control import evaluate_publication_gate, validate_publication_decision

def _report():
    return {"report_id":"R1","claim_evidence_limitation_matrix":[
        {"claim_id":"C1","source_ids":["P1"],"sample_size":5,"limitations":["Small sample."]}]}

def test_publication_gate_requires_explicit_human_signoff():
    decision=evaluate_publication_gate(report=_report(),graph_validation={"valid":True})
    assert decision.status=="CONTROL_REQUIRED"
    assert "human_signoff" in decision.blockers

def test_publication_gate_approves_only_when_all_gates_pass():
    decision=evaluate_publication_gate(report=_report(),graph_validation={"valid":True},
        reviewer_id="reviewer-1",rationale="Reviewed evidence and limitations.")
    assert decision.status=="APPROVED_FOR_PUBLICATION"
    assert validate_publication_decision(decision)["valid"] is True

def test_publication_gate_blocks_invalid_graph_and_unsupported_claim():
    report=_report()
    report["claim_evidence_limitation_matrix"].append({"claim_id":"C2","source_ids":[],"sample_size":0,"limitations":["No source."]})
    decision=evaluate_publication_gate(report=report,graph_validation={"valid":False},
        reviewer_id="reviewer-1",rationale="Reviewed.")
    assert decision.status=="CONTROL_REQUIRED"
    assert "graph_valid" in decision.blockers
    assert "all_claims_sourced" in decision.blockers

def test_publication_gate_blocks_missing_limitations_and_bad_sample_size():
    report=_report()
    report["claim_evidence_limitation_matrix"][0]["limitations"]=[]
    report["claim_evidence_limitation_matrix"][0]["sample_size"]=-1
    decision=evaluate_publication_gate(report=report,graph_validation={"valid":True},
        reviewer_id="reviewer-1",rationale="Reviewed.")
    assert "claim_limitations_present" in decision.blockers
    assert "sample_sizes_disclosed" in decision.blockers
