import json
import pytest

from nema_agora.evaluation import (
    EvaluationCase,
    build_report,
    evaluate_category,
    evaluate_duplicate,
    evaluate_summary_faithfulness,
    serialise_report,
    validate_advisory_output,
)
from nema_agora.core import CATEGORIES


def case(case_id, category=CATEGORIES[0], duplicate=False, faithful=None):
    return EvaluationCase(case_id, category, duplicate, faithful)


def test_category_accuracy():
    cases=[case("1"), case("2", CATEGORIES[1])]
    assert evaluate_category(cases, {"1": CATEGORIES[0], "2": CATEGORIES[0]}) == 0.5


def test_duplicate_precision_recall_f1():
    cases=[case("1", duplicate=True), case("2"), case("3", duplicate=True)]
    assert evaluate_duplicate(cases, {"1": True, "2": True, "3": False}) == pytest.approx((0.5, 0.5, 0.5))


def test_summary_faithfulness_requires_human_labels():
    cases=[case("1", faithful=True), case("2", faithful=False), case("3")]
    assert evaluate_summary_faithfulness(cases) == pytest.approx(0.5)
    assert evaluate_summary_faithfulness([case("4")]) is None


def test_report_is_reproducible_and_serialisable():
    report=build_report([case("1", duplicate=True)], {"1": CATEGORIES[0]}, {"1": True})
    payload=serialise_report(report)
    assert json.loads(payload)["category_accuracy"] == 1.0


def test_invalid_category_is_rejected():
    with pytest.raises(ValueError):
        case("1", "not-supported")


@pytest.mark.parametrize("output", [
    {"source_case_id":"1", "human_review_required":True, "enforcement_action":"close"},
    {"source_case_id":"1", "human_review_required":False},
    {"human_review_required":True},
])
def test_autonomous_decision_output_is_rejected(output):
    assert validate_advisory_output(output)


def test_safe_advisory_output_is_accepted():
    assert validate_advisory_output({"source_case_id":"1", "human_review_required":True}) == []
