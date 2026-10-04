from nema_agora.evaluation import EvaluationReport
from nema_agora.observatory import build_observatory_snapshot


def report(cases=25, accuracy=0.8, duplicate_f1=0.8, faithfulness=0.9):
    return EvaluationReport(
        category_accuracy=accuracy,
        duplicate_precision=0.8,
        duplicate_recall=0.8,
        duplicate_f1=duplicate_f1,
        summary_faithfulness_rate=faithfulness,
        cases_evaluated=cases,
    )


def event(kind):
    return {"event_type": "feedback_recorded", "details": {"feedback_type": kind}}


def test_readiness_requires_all_gates():
    snapshot = build_observatory_snapshot(
        report(), [event("accepted")] * 20
    )
    assert snapshot.readiness == "READY_FOR_REVIEW"
    assert all(g.passed for g in snapshot.gates)


def test_correction_rate_is_visible():
    snapshot = build_observatory_snapshot(
        report(), [event("accepted")] * 8 + [event("corrected")] * 2
    )
    assert snapshot.correction_rate == 0.2
    assert snapshot.corrected == 2


def test_missing_feedback_or_weak_metrics_blocks_readiness():
    snapshot = build_observatory_snapshot(
        report(cases=24, accuracy=0.79), [event("accepted")] * 19
    )
    assert snapshot.readiness == "NOT_READY"
    assert any(not gate.passed for gate in snapshot.gates)


def test_unmeasured_summary_faithfulness_blocks_readiness():
    snapshot = build_observatory_snapshot(
        report(faithfulness=None), [event("accepted")] * 20
    )
    assert snapshot.readiness == "NOT_READY"
