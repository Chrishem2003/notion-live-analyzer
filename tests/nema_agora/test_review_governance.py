from nema_agora.review_governance import REVIEW_DECISIONS, build_reevaluation, make_lifecycle_decision, make_shadow_review

def _run(run_id="CSR-1", admission_id="ADM-1", status="SHADOW_OK"):
    return {"run_id": run_id, "admission_id": admission_id, "case_id": "CASE-1", "status": status,
            "output": {"source_case_id": "CASE-1", "human_review_required": True}}

def test_review_is_bounded_and_run_bound():
    review = make_shadow_review(run=_run(), reviewer_id="reviewer-1", decision="CONFIRMED_USEFUL", notes="Useful.")
    assert review.run_id == "CSR-1"
    assert review.admission_id == "ADM-1"
    assert review.decision in REVIEW_DECISIONS

def test_reevaluation_retain_after_ten_clean_reviews():
    runs = [_run(f"CSR-{i}") for i in range(10)]
    reviews = [{"run_id": f"CSR-{i}", "admission_id": "ADM-1", "decision": "CONFIRMED_USEFUL"} for i in range(10)]
    result = build_reevaluation(runs, reviews, admission_id="ADM-1")
    assert result["recommendation"] == "RETAIN"
    assert result["reviewed_runs"] == 10

def test_unsafe_review_forces_suspend():
    runs = [_run("CSR-1")]
    reviews = [{"run_id": "CSR-1", "admission_id": "ADM-1", "decision": "UNSAFE"}]
    result = build_reevaluation(runs, reviews, admission_id="ADM-1", minimum_reviewed_runs=1)
    assert result["recommendation"] == "SUSPEND"
    assert "UNSAFE_REVIEW_RATE_ABOVE_POLICY" in result["alerts"]

def test_correction_rate_triggers_review():
    runs = [_run(f"CSR-{i}") for i in range(10)]
    reviews = [{"run_id": f"CSR-{i}", "admission_id": "ADM-1",
                "decision": "NEEDS_CORRECTION" if i < 2 else "CONFIRMED_USEFUL"} for i in range(10)]
    result = build_reevaluation(runs, reviews, admission_id="ADM-1")
    assert result["recommendation"] == "REVIEW"
    assert result["correction_rate"] == 0.2

def test_lifecycle_decision_binds_candidate():
    admission = {"admission_id": "ADM-1", "result": {
        "decision": "ADMITTED_FOR_CONTROLLED_SHADOW",
        "candidate": {"provider": "provider-a", "model_version": "model-1", "adapter_name": "adapter-a"}}}
    decision = make_lifecycle_decision(admission=admission, action="REVIEW", decided_by="coord-1",
                                       rationale="Review more evidence.", evidence_snapshot={"reviewed_runs": 10})
    assert decision.provider == "provider-a"
    assert decision.action == "REVIEW"
