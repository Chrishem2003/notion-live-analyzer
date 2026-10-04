from nema_agora.evaluation import EvaluationCase,build_evaluation_run,validate_evaluation_run

def test_evaluation_is_reproducible_and_advisory():
    cases=[EvaluationCase("c1","fp1","A","A","model","1"),EvaluationCase("c2","fp2","A","B","model","1")]
    run=build_evaluation_run(run_id="run1",dataset={"dataset":"pilot","version":1},cases=cases)
    assert run.accuracy==0.5
    result=validate_evaluation_run(run)
    assert result["valid"] and result["reproducible"]
    assert result["automatic_model_admission"] is False
