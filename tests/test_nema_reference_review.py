"""Tests for independent reference-review metadata gate."""
import pytest

from nema_agora.reference_review import ReferenceReviewError, validate_reference_review_package


def unit(unit_id="wetland-001", **overrides):
    value = {
        "unit_id": unit_id,
        "reference_change": True,
        "reviewer_ids": ["reviewer-a", "reviewer-b"],
        "reviewed_at": "2026-02-01T10:30:00Z",
        "evidence_refs": ["imagery:S2A_product_001", "field-note:FN-001"],
        "reviewers_blinded_to_candidate": True,
    }
    value.update(overrides)
    return value


def package(**overrides):
    value = {
        "reference_set_id": "uganda-wetland-ref",
        "reference_set_version": "v1",
        "split": "holdout",
        "units": [unit()],
    }
    value.update(overrides)
    return value


def test_valid_package_returns_stable_digest_and_non_authenticated_state():
    first = validate_reference_review_package(package())
    second = validate_reference_review_package(package())
    assert first["state"] == "REVIEW_METADATA_COMPLETE_NOT_AUTHENTICATED"
    assert first["package_sha256"] == second["package_sha256"]
    assert len(first["package_sha256"]) == 64
    assert first["unit_count"] == 1
    assert any("do not prove actual independence" in s for s in first["limitations"])


@pytest.mark.parametrize("changes, message", [
    ({"reviewer_ids": ["reviewer-a"]}, "at least two"),
    ({"reviewer_ids": ["same", "same"]}, "distinct"),
    ({"reviewed_at": "2026-02-01T10:30:00"}, "timezone"),
    ({"evidence_refs": []}, "evidence reference"),
    ({"reviewers_blinded_to_candidate": False}, "blinded"),
    ({"reference_change": "true"}, "boolean"),
])
def test_incomplete_review_metadata_is_rejected(changes, message):
    with pytest.raises(ReferenceReviewError, match=message):
        validate_reference_review_package(package(units=[unit(**changes)]))


def test_duplicate_reference_units_are_rejected():
    with pytest.raises(ReferenceReviewError, match="duplicate unit_id"):
        validate_reference_review_package(package(units=[unit(), unit()]))


def test_invalid_split_is_rejected():
    with pytest.raises(ReferenceReviewError, match="split"):
        validate_reference_review_package(package(split="final"))
