import pytest

from nema_agora.annotation import AnnotationStore, make_annotation, pairwise_agreement
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
