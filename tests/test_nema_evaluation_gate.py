"""Tests for the fail-closed NEMA-AGORA holdout evaluation gate."""
import pytest

from nema_agora.evaluation_gate import EvaluationGateError, evaluate_holdout_package


def review(split="holdout", units=None):
    if units is None:
        units = [
            {"unit_id": "h-1", "reference_change": True, "reviewer_ids": ["r1", "r2"],
             "reviewed_at": "2026-03-01T10:00:00Z", "evidence_refs": ["evidence:1"],
             "reviewers_blinded_to_candidate": True},
            {"unit_id": "h-2", "reference_change": False, "reviewer_ids": ["r1", "r2"],
             "reviewed_at": "2026-03-01T10:05:00Z", "evidence_refs": ["evidence:2"],
             "reviewers_blinded_to_candidate": True},
        ]
    return {"reference_set_id": "uganda-ref", "reference_set_version": "v1", "split": split, "units": units}


def manifests(overlap=False):
    return [
        {"reference_set_id": "uganda-ref", "reference_set_version": "v1", "split": "development",
         "unit_ids": ["d-1", "h-1"] if overlap else ["d-1"]},
        {"reference_set_id": "uganda-ref", "reference_set_version": "v1", "split": "validation", "unit_ids": ["v-1"]},
        {"reference_set_id": "uganda-ref", "reference_set_version": "v1", "split": "holdout", "unit_ids": ["h-1", "h-2"]},
    ]


def spatial_units(overlap=False):
    holdout_box = [28.05, -0.95, 28.15, -0.85] if overlap else [31.0, 1.0, 31.1, 1.1]
    return [
        {"unit_id": "d-1", "split": "development", "bbox_wgs84": [28.0, -1.0, 28.1, -0.9],
         "observation_start": "2024-01-01T00:00:00Z", "observation_end": "2024-01-02T00:00:00Z"},
        {"unit_id": "v-1", "split": "validation", "bbox_wgs84": [30.0, 0.0, 30.1, 0.1],
         "observation_start": "2024-06-01T00:00:00Z", "observation_end": "2024-06-02T00:00:00Z"},
        {"unit_id": "h-1", "split": "holdout", "bbox_wgs84": holdout_box,
         "observation_start": "2025-01-01T00:00:00Z", "observation_end": "2025-01-02T00:00:00Z"},
        {"unit_id": "h-2", "split": "holdout", "bbox_wgs84": [32.0, 2.0, 32.1, 2.1],
         "observation_start": "2025-06-01T00:00:00Z", "observation_end": "2025-06-02T00:00:00Z"},
    ]


def records():
    return [
        {"unit_id": "h-1", "area_ha": 0.5, "detected": True, "reference_change": True,
         "independently_verified": True, "usable": True},
        {"unit_id": "h-2", "area_ha": 0.5, "detected": True, "reference_change": False,
         "independently_verified": True, "usable": True},
    ]


def test_holdout_gate_computes_metrics_only_for_exactly_matching_declared_units():
    result = evaluate_holdout_package(reference_review_package=review(), split_manifests=manifests(),
                                      evaluation_records=records(), spatiotemporal_units=spatial_units())
    assert result["decision"] == "METRICS_COMPUTED_WITH_DECLARED_GATES"
    assert result["holdout_unit_count"] == 2
    assert result["evaluation"]["counts"]["true_positive"] == 1
    assert result["evaluation"]["counts"]["false_positive"] == 1
    assert result["state"] == "HOLDOUT_METRICS_COMPUTED_DECLARATIONS_NOT_AUTHENTICATED"


@pytest.mark.parametrize("review_package, split_data, eval_data, message", [
    (review(split="development"), manifests(), records(), "split='holdout'"),
    (review(), manifests(overlap=True), records(), "overlap"),
    (review(units=[{"unit_id": "h-1", "reference_change": True, "reviewer_ids": ["r1", "r2"],
                   "reviewed_at": "2026-03-01T10:00:00Z", "evidence_refs": ["evidence:1"],
                   "reviewers_blinded_to_candidate": True}]), manifests(), records(), "exactly match"),
    (review(), manifests(), [records()[0]], "exactly match"),
    (review(), manifests(), [dict(records()[0], reference_change=False), records()[1]], "does not match"),
])
def test_holdout_gate_fails_closed(review_package, split_data, eval_data, message):
    with pytest.raises(EvaluationGateError, match=message):
        evaluate_holdout_package(reference_review_package=review_package, split_manifests=split_data,
                                 evaluation_records=eval_data, spatiotemporal_units=spatial_units())


def test_holdout_gate_blocks_spatial_or_temporal_overlap():
    with pytest.raises(EvaluationGateError, match="spatial/temporal overlap"):
        evaluate_holdout_package(reference_review_package=review(), split_manifests=manifests(),
                                 evaluation_records=records(), spatiotemporal_units=spatial_units(overlap=True))


def test_holdout_gate_preserves_explicit_exclusions():
    bad = records()
    bad[0]["independently_verified"] = False
    result = evaluate_holdout_package(reference_review_package=review(), split_manifests=manifests(),
                                      evaluation_records=bad, spatiotemporal_units=spatial_units())
    assert result["evaluation"]["counts"]["eligible_units"] == 1
    assert result["evaluation"]["counts"]["excluded_units"] == 1
