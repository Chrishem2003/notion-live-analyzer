from nema_agora.evidence_observatory import build_observatory

def test_control_required_on_integrity_failure():
    out=build_observatory(attestations=[{"effective_state":"ATTESTED"}],lifecycle_items=[],provenance_result={"bindings":[],"failures":[],"valid_count":0},integrity_valid=False,provenance_complete=True)
    assert out["overall_state"]=="CONTROL_REQUIRED"
    assert "INTEGRITY_FAILED" in out["gaps"]

def test_readiness_is_not_authorization():
    out=build_observatory(attestations=[{"effective_state":"ATTESTED"}],lifecycle_items=[{"lifecycle_state":"ACTIVE"}],provenance_result={"bindings":[{"binding_id":"b"}],"failures":[],"valid_count":1},integrity_valid=True,provenance_complete=True)
    assert out["overall_state"]=="EVIDENCE_COVERAGE_OK"
    assert "NEMA authorization" in out["notice"]
