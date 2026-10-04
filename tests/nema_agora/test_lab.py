import pytest

from nema_agora.core import CATEGORIES
from nema_agora.lab import LabCase, run_evaluation


class GoodAdapter:
    provider = "local-test"
    model_version = "good-v1"

    def analyse(self, record):
        return {
            "source_case_id": record["case_id"],
            "human_review_required": True,
            "predicted_category": record["category"],
            "duplicate_candidates": [],
            "confidence": 0.9,
        }


class UnsafeAdapter:
    provider = "unsafe"
    model_version = "bad-v1"

    def analyse(self, record):
        return {
            "source_case_id": record["case_id"],
            "human_review_required": True,
            "enforcement_action": "dispatch",
        }


def case(i="1", duplicate=False):
    cid = f"LAB-{i}"
    return LabCase(
        cid,
        {"case_id": cid, "category": CATEGORIES[0], "description": "synthetic"},
        CATEGORIES[0],
        duplicate,
        True,
        "solid-waste",
    )


def test_lab_computes_metrics_and_slices():
    result = run_evaluation([case("1"), case("2")], {"good": GoodAdapter()}, dataset_version="v1")
    metrics = result.adapters[0]
    assert metrics.category_accuracy == 1.0
    assert metrics.duplicate_f1 == 0.0
    assert metrics.confidence_brier == pytest.approx(0.01)
    assert result.slice_results[0]["slice"] == "solid-waste"
    assert result.readiness == "NOT_READY"


def test_lab_contains_source_bound_case_results():
    result = run_evaluation([case("1")], {"good": GoodAdapter()}, dataset_version="v1")
    assert result.case_results[0]["case_id"] == "LAB-1"
    assert result.case_results[0]["status"] == "OK"


def test_lab_fails_unsafe_adapter_safely():
    result = run_evaluation([case("1")], {"unsafe": UnsafeAdapter()}, dataset_version="v1")
    assert result.adapters[0].failures == 1
    assert result.case_results[0]["status"] == "ERROR"
    assert "enforcement_action" in result.case_results[0]["error"]


def test_lab_requires_real_labels():
    with pytest.raises(ValueError):
        LabCase("x", {"case_id": "y"}, CATEGORIES[0], False)
