"""Tests for declared dataset split leakage audit."""
import pytest

from nema_agora.split_audit import SplitAuditError, audit_dataset_splits


def manifest(split, unit_ids, version="v1"):
    return {
        "reference_set_id": "uganda-wetland-ref",
        "reference_set_version": version,
        "split": split,
        "unit_ids": unit_ids,
    }


def test_disjoint_three_way_splits_pass_as_declarations_only():
    report = audit_dataset_splits([
        manifest("development", ["site-01", "site-02"]),
        manifest("validation", ["site-03"]),
        manifest("holdout", ["site-04"]),
    ])
    assert report["decision"] == "NO_DECLARED_UNIT_ID_OVERLAP"
    assert report["state"] == "DECLARED_SPLITS_DISJOINT_NOT_AUTHENTICATED"
    assert report["split_unit_counts"]["uganda-wetland-ref"]["holdout"] == 1
    assert len(report["manifest_sha256"]) == 64
    assert any("does not prove" in item for item in report["limitations"])


def test_overlap_between_splits_blocks_evaluation():
    report = audit_dataset_splits([
        manifest("development", ["site-01", "site-02"]),
        manifest("holdout", ["site-02"]),
    ])
    assert report["decision"] == "BLOCK_EVALUATION"
    assert report["overlaps"][0]["overlapping_unit_ids"] == ["site-02"]


def test_overlap_is_detected_even_across_manifest_versions():
    report = audit_dataset_splits([
        manifest("development", ["site-01"], "v1"),
        manifest("holdout", ["site-01"], "v2"),
    ])
    assert report["decision"] == "BLOCK_EVALUATION"


@pytest.mark.parametrize("manifests, message", [
    ([], "non-empty"),
    ([manifest("final", ["x"])], "split"),
    ([manifest("holdout", [])], "non-empty array"),
    ([manifest("holdout", ["x", "x"])], "duplicate unit ID"),
    ([manifest("holdout", ["x"]), manifest("holdout", ["y"])], "duplicate manifest"),
    ([{"reference_set_id": "bad space", "reference_set_version": "v1", "split": "holdout", "unit_ids": ["x"]}], "reference_set_id"),
])
def test_malformed_split_manifests_fail_closed(manifests, message):
    with pytest.raises(SplitAuditError, match=message):
        audit_dataset_splits(manifests)


def test_manifest_digest_is_order_independent():
    left = audit_dataset_splits([
        manifest("development", ["b", "a"]),
        manifest("holdout", ["c"]),
    ])
    right = audit_dataset_splits([
        manifest("holdout", ["c"]),
        manifest("development", ["a", "b"]),
    ])
    assert left["manifest_sha256"] == right["manifest_sha256"]
