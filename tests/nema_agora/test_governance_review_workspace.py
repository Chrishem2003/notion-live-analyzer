from nema_agora.governance_review_workspace import build_workspace

def _case():
    return {"case_id":"CASE-1","code":"ORPHAN_ATTESTATION","severity":"HIGH","required_action":"HUMAN_REVIEW_REQUIRED",
            "accountable_artifacts":{"attestation_ids":["ATT-1"],"decision_ids":["LIFE-1"],"binding_ids":["BIND-1"]},
            "finding":{"code":"ORPHAN_ATTESTATION"}}

def test_workspace_projects_selected_case_and_queue_context():
    out=build_workspace(queue_result={"queue":[{"case_id":"CASE-1","queue_position":1,"severity":"HIGH"}]},
        casebook={"cases":[_case()]},attestations=[{"attestation_id":"ATT-1"}],
        lifecycle_items=[{"attestation_id":"ATT-1","lifecycle_state":"ACTIVE"}],
        lifecycle_decisions=[{"decision_id":"LIFE-1","attestation_id":"ATT-1","actor_id":"R"}],
        bindings=[{"binding_id":"BIND-1","attestation_id":"ATT-1"}],
        provenance_result={"bindings":[{"binding_id":"BIND-1","state":"VALID"}],"failures":[]},
        current_snapshot={"reconciliation_fingerprint":"r","evidence_registry_fingerprint":"e","provenance_fingerprint":"p"},case_id="CASE-1")
    assert out["state"]=="READY_FOR_HUMAN_REVIEW"
    assert out["case"]["queue_context"]["queue_position"]==1
    assert out["case"]["provenance_bindings"][0]["validation_state"]=="VALID"

def test_workspace_is_deterministic():
    args=dict(queue_result={"queue":[{"case_id":"CASE-1","queue_position":1}]},casebook={"cases":[_case()]},
        attestations=[],lifecycle_items=[],lifecycle_decisions=[],bindings=[],provenance_result={"bindings":[],"failures":[]},
        current_snapshot={"reconciliation_fingerprint":"r","evidence_registry_fingerprint":"e","provenance_fingerprint":"p"},case_id="CASE-1")
    assert build_workspace(**args)["workspace_fingerprint"]==build_workspace(**args)["workspace_fingerprint"]

def test_missing_case_fails_closed():
    out=build_workspace(queue_result={"queue":[]},casebook={"cases":[]},attestations=[],lifecycle_items=[],lifecycle_decisions=[],bindings=[],
        provenance_result={},current_snapshot={},case_id="CASE-X")
    assert out["state"]=="CASE_NOT_FOUND"
