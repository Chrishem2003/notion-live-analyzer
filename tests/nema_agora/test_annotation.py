import pytest

from nema_agora.annotation import AnnotationStore, annotation_readiness, make_adjudication, make_annotation, pairwise_agreement
from nema_agora.core import CATEGORIES


def ann(case_id, who, category=None, duplicate=False):
    return make_annotation(
        case_id=case_id,
        annotator_id=who,
        dataset_version="dataset-v1",
        category=category or CATEGORIES[0],
        duplicate=duplicate,
        summary_faithful=True,
        notes="",
    )


def test_pairwise_agreement_measures_category_and_duplicate():
    a = [ann("1", "a"), ann("2", "a", CATEGORIES[1], True)]
    b = [ann("1", "b"), ann("2", "b", CATEGORIES[1], False)]
    result = pairwise_agreement(a, b)
    assert result["cases_compared"] == 2
    assert result["category_observed_agreement"] == 1.0
    assert result["category_cohen_kappa"] == pytest.approx(1.0)
    assert result["duplicate_observed_agreement"] == 0.5


def test_store_enforces_one_independent_label_per_annotator_and_dataset(tmp_path):
    store = AnnotationStore(str(tmp_path / "annotations.sqlite3"))
    first = ann("1", "reviewer-a")
    store.save(first)
    with pytest.raises(Exception):
        store.save(ann("1", "reviewer-a"))


def test_blind_case_listing_is_separate_from_annotator_listing(tmp_path):
    store = AnnotationStore(str(tmp_path / "annotations.sqlite3"))
    store.save(ann("1", "reviewer-a"))
    store.save(ann("1", "reviewer-b", CATEGORIES[1]))
    assert len(store.list_for_annotator("reviewer-a", "dataset-v1")) == 1
    assert len(store.list_for_case("1", "dataset-v1")) == 2


def test_annotation_rejects_invalid_category():
    with pytest.raises(ValueError):
        make_annotation(
            case_id="1", annotator_id="a", dataset_version="v1",
            category="not-real", duplicate=False, summary_faithful=None
        )


def test_annotation_readiness_requires_process_gates():
    a = [ann("1", "a"), ann("2", "a")]
    result = annotation_readiness(a, [], minimum_cases=2)
    assert result["status"] == "NOT_READY"
    assert not result["gates"]["two_independent_annotators"]


def test_annotation_readiness_requires_adjudicating_disagreements():
    first = [ann("1", "a")]
    second = [ann("1", "b", CATEGORIES[1])]
    result = annotation_readiness(first + second, [], minimum_cases=1, minimum_category_kappa=-1.0)
    assert "1" in result["unresolved_disagreements"]
    assert result["status"] == "NOT_READY"
    adjudication = make_adjudication(
        case_id="1", adjudicator_id="admin", dataset_version="dataset-v1",
        final_category=CATEGORIES[0], final_duplicate=False,
        final_summary_faithful=True, rationale="Resolved by documented adjudication.",
    )
    result2 = annotation_readiness(first + second, [adjudication], minimum_cases=1, minimum_category_kappa=-1.0)
    assert result2["status"] == "READY_FOR_REVIEW"
