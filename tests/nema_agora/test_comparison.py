from __future__ import annotations
import copy
import pytest
from nema_agora.comparison import FrozenCase, compare_models, freeze_dataset
from nema_agora.evaluation import SUPPORTED_CATEGORIES
from nema_agora.shadow import DeterministicShadowAdapter

def case(i: int) -> FrozenCase:
    return FrozenCase(f"CASE-{i:03d}", {"case_id":f"CASE-{i:03d}","description":f"synthetic {i}"},
                      SUPPORTED_CATEGORIES[i % len(SUPPORTED_CATEGORIES)], i % 3 == 0, True, "synthetic")

class UnsafeAdapter:
    provider="test"; model_version="unsafe-v1"
    def analyse(self, record):
        return {"source_case_id":record["case_id"],"human_review_required":True,"enforcement_action":"dispatch"}

def test_freeze_hash_is_order_independent():
    cases=[case(i) for i in range(3)]
    a=freeze_dataset(cases,"ds-v1",frozen_at="2026-01-01T00:00:00+00:00")
    b=freeze_dataset(list(reversed(cases)),"ds-v1",frozen_at="2026-01-01T00:00:00+00:00")
    assert a.manifest_hash == b.manifest_hash

def test_comparison_is_bound_and_non_mutating():
    cases=[case(i) for i in range(25)]; before=copy.deepcopy(cases)
    manifest=freeze_dataset(cases,"ds-v1",frozen_at="2026-01-01T00:00:00+00:00")
    result=compare_models(cases,{"deterministic":BenchmarkAdapter()},dataset=manifest)
    assert result.dataset.manifest_hash == manifest.manifest_hash
    assert result.readiness == "READY_FOR_REVIEW"
    assert cases == before

def test_unsafe_adapter_fails_closed():
    cases=[case(i) for i in range(25)]
    result=compare_models(cases,{"unsafe":UnsafeAdapter()},dataset=freeze_dataset(cases,"ds-v1"))
    assert result.adapters[0].failures == 25
    assert result.readiness == "NOT_READY"
    assert all(r["status"]=="ERROR" for r in result.case_results)

def test_manifest_mismatch_rejected():
    cases=[case(i) for i in range(2)]; manifest=freeze_dataset(cases,"ds-v1")
    with pytest.raises(ValueError):
        compare_models(cases[:1],{"baseline":DeterministicShadowAdapter()},dataset=manifest)


def test_comparison_store_persists_immutable_summary(tmp_path):
    from nema_agora.comparison import ComparisonRunStore
    cases=[case(i) for i in range(25)]
    manifest=freeze_dataset(cases,"ds-v1",frozen_at="2026-01-01T00:00:00+00:00")
    result=compare_models(cases,{"baseline":DeterministicShadowAdapter()},dataset=manifest)
    store=ComparisonRunStore(str(tmp_path/"nema.db"))
    store.save(result,actor_id="reviewer-1")
    rows=store.list(limit=10)
    assert rows[0]["run_id"] == result.run_id
    assert rows[0]["dataset_version"] == "ds-v1"
    assert rows[0]["manifest_hash"] == manifest.manifest_hash
    assert rows[0]["actor_id"] == "reviewer-1"

class BenchmarkAdapter:
    provider="test"; model_version="benchmark-v1"
    def analyse(self, record):
        i=int(record["case_id"].split("-")[1])
        return {"source_case_id":record["case_id"],"predicted_category":SUPPORTED_CATEGORIES[i % len(SUPPORTED_CATEGORIES)],"duplicate_candidates":[{"case_id":"DUP"}] if i % 3 == 0 else [],"human_review_required":True}

class MissingCategoryAdapter:
    provider="test"; model_version="missing-category-v1"
    def analyse(self, record):
        return {"source_case_id":record["case_id"],"human_review_required":True}

class FixedAdapter:
    provider="test"; model_version="fixed-v1"
    def analyse(self, record):
        return {"source_case_id":record["case_id"],"predicted_category":SUPPORTED_CATEGORIES[0],
                "duplicate_candidates":[],"human_review_required":True}

def test_missing_predictions_are_counted_as_accuracy_misses():
    cases=[case(i) for i in range(25)]
    result=compare_models(cases,{"missing":MissingCategoryAdapter()},dataset=freeze_dataset(cases,"ds-v1"))
    assert result.adapters[0].category_accuracy == 0.0
    assert result.adapters[0].category_macro_recall < 1.0

def test_second_adapter_produces_disagreement_and_regression():
    cases=[case(i) for i in range(25)]
    result=compare_models(
        cases,
        {"baseline":BenchmarkAdapter(),"candidate":FixedAdapter()},
        dataset=freeze_dataset(cases,"ds-v1"),
        baseline_adapter="baseline",
    )
    assert result.regression
    assert result.model_disagreement
    assert result.regression[0]["adapter"] == "candidate"
