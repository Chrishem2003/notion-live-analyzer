from nema_agora.governance_review_queue import build_review_queue
def snap(): return {"reconciliation_fingerprint":"r","evidence_registry_fingerprint":"e","provenance_fingerprint":"p"}
def test_priority_is_deterministic():
    cases=[{"case_id":"B","code":"X","severity":"LOW","required_action":"HUMAN_REVIEW_REQUIRED","finding":{"age_days":2}},{"case_id":"A","code":"Y","severity":"CRITICAL","required_action":"HUMAN_REVIEW_REQUIRED","finding":{"age_days":1}}]
    out=build_review_queue(cases=cases,current_snapshot=snap())
    assert [x["case_id"] for x in out["queue"]]==["A","B"]
    assert out["queue"][0]["queue_position"]==1
def test_age_and_dependency_are_exposed():
    out=build_review_queue(cases=[{"case_id":"A","code":"X","severity":"HIGH","required_action":"HUMAN_REVIEW_REQUIRED","finding":{"age_days":12,"dependency":"B"}}],current_snapshot=snap())
    row=out["queue"][0]
    assert row["age_days"]==12 and row["dependency"] is True
def test_empty_queue():
    assert build_review_queue(cases=[],current_snapshot=snap())["overall_state"]=="EMPTY"
