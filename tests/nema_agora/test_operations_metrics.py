from nema_agora.operations_metrics import summarize_case_metrics,validate_case_metrics
def test_metrics_are_bounded_and_advisory():
    metrics=summarize_case_metrics([])
    assert metrics["case_count"]==0 and metrics["human_review_coverage"]==0
    assert validate_case_metrics(metrics)["valid"]
    assert metrics["execution_gate"]=="CLOSED"
