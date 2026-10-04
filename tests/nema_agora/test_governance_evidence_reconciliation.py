from nema_agora.governance_evidence_reconciliation import reconcile
def snap(): return {"reconciliation_fingerprint":"r","evidence_registry_fingerprint":"e","provenance_fingerprint":"p"}
def test_clean_chain_reconciles():
    a={"attestation_id":"ATT-1"}; l={"attestation_id":"ATT-1","lifecycle_state":"PENDING_REVIEW","latest_decision":None}
    b={"binding_id":"B-1","attestation_id":"ATT-1","decision_id":"LIFE-1","reconciliation_fingerprint":"r","evidence_registry_fingerprint":"e","provenance_fingerprint":"p"}
    assert reconcile(attestations=[a],lifecycle_items=[l],bindings=[b],provenance_result={"failures":[]},current_snapshot=snap())["state"]=="RECONCILED"
def test_conflicts_fail_closed():
    out=reconcile(attestations=[{"attestation_id":"ATT-1"}],lifecycle_items=[],bindings=[{"binding_id":"B","attestation_id":"ATT-2","decision_id":"LIFE-2","reconciliation_fingerprint":"wrong","evidence_registry_fingerprint":"e","provenance_fingerprint":"p"}],provenance_result={"failures":[{"reason":"BAD"}]},current_snapshot=snap())
    codes={x["code"] for x in out["findings"]}
    assert out["state"]=="CONTROL_REQUIRED"
    assert {"ORPHAN_ATTESTATION","ORPHAN_PROVENANCE_BINDING","PROVENANCE_SNAPSHOT_MISMATCH","PROVENANCE_VALIDATION_FAILURE"} <= codes
def test_active_requires_binding():
    out=reconcile(attestations=[{"attestation_id":"ATT-1"}],lifecycle_items=[{"attestation_id":"ATT-1","lifecycle_state":"ACTIVE","latest_decision":None}],bindings=[],provenance_result={"failures":[]},current_snapshot=snap())
    assert any(x["code"]=="ACTIVE_WITHOUT_PROVENANCE_BINDING" for x in out["findings"])
