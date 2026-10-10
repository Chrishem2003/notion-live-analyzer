from nema_agora.governance_review_decision import prepare_review_decision

def _workspace():
    return {"state":"READY_FOR_HUMAN_REVIEW","case":{"case_id":"CASE-1","required_action":"HUMAN_REVIEW_REQUIRED",
        "queue_context":{"queue_position":1,"accountable_artifacts":{"attestation_ids":["A"]}},
        "finding":{"code":"X"},"attestations":[],"lifecycle_items":[],"lifecycle_decisions":[],"provenance_bindings":[]}}

def test_prepares_without_deciding():
    out=prepare_review_decision(workspace=_workspace(),current_snapshot={"r":"x"},reviewer_actor_id="reviewer-1")
    assert out["state"]=="READY_FOR_HUMAN_DECISION"
    assert out["decision_status"]=="NOT_DECIDED"
    assert out["package"]["prepared_by"]=="reviewer-1"

def test_missing_case_fails_closed():
    out=prepare_review_decision(workspace={"state":"EMPTY","case":None},current_snapshot={},reviewer_actor_id="r")
    assert out["state"]=="NOT_READY"

def test_reviewer_is_required():
    try:
        prepare_review_decision(workspace=_workspace(),current_snapshot={},reviewer_actor_id="")
    except ValueError as exc:
        assert "reviewer_actor_id" in str(exc)
    else:
        raise AssertionError("expected ValueError")
