from nema_agora.governance_evidence_casebook import build_casebook
def snap(): return {"reconciliation_fingerprint":"r","evidence_registry_fingerprint":"e","provenance_fingerprint":"p"}
def test_casebook_links_related_artifacts():
    out=build_casebook(reconciliation_result={"findings":[{"code":"ORPHAN_ATTESTATION","attestation_id":"ATT-1"}]},attestations=[{"attestation_id":"ATT-1"}],lifecycle_items=[{"attestation_id":"ATT-1"}],lifecycle_decisions=[{"decision_id":"LIFE-1","attestation_id":"ATT-1"}],bindings=[{"binding_id":"B-1","attestation_id":"ATT-1","decision_id":"LIFE-1"}],current_snapshot=snap())
    assert out["case_count"]==1
    assert out["cases"][0]["required_action"]=="HUMAN_REVIEW_REQUIRED"
    assert out["cases"][0]["accountable_artifacts"]=={"attestation_ids":["ATT-1"],"decision_ids":["LIFE-1"],"binding_ids":["B-1"]}
def test_casebook_is_deterministic():
    kwargs=dict(reconciliation_result={"findings":[{"code":"X","attestation_id":"A"}]},attestations=[{"attestation_id":"A"}],lifecycle_items=[],lifecycle_decisions=[],bindings=[],current_snapshot=snap())
    assert build_casebook(**kwargs)["casebook_fingerprint"]==build_casebook(**kwargs)["casebook_fingerprint"]
def test_empty_casebook():
    out=build_casebook(reconciliation_result={"findings":[]},attestations=[],lifecycle_items=[],lifecycle_decisions=[],bindings=[],current_snapshot=snap())
    assert out["overall_state"]=="NO_CASES" and out["case_count"]==0
