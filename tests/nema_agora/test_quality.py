"""Regression tests for deterministic observation quality gates."""
import pytest

from nema_agora.quality import assess_observation


def sample(**updates):
    record = {
        "case_id": "NA-TEST001",
        "observation_date": "2026-10-01",
        "category": "Water pollution",
        "severity": "Moderate",
        "district_or_site": "Pilot Site A",
        "description": "Synthetic observation of water discoloration",
        "status": "Under review",
        "consent_confirmed": True,
        "latitude": 2.5,
        "longitude": 32.1,
    }
    record.update(updates)
    return record


def test_complete_record_passes_but_still_requires_human_review():
    result = assess_observation(sample())
    assert result["quality_status"] == "PASS"
    assert result["flags"] == ["VALID"]
    assert result["human_review_required"] is True
    assert result["environmental_truth_claim"] is False
    assert result["regulatory_conclusion"] is False
    assert result["automatic_enforcement"] is False


@pytest.mark.parametrize(
    "updates,expected_flag",
    [
        ({"description": None}, "INCOMPLETE"),
        ({"description": "  "}, "MISSING_DESCRIPTION"),
        ({"consent_confirmed": 1}, "MISSING_CONSENT"),
        ({"latitude": 91.0}, "INVALID_COORDINATES"),
        ({"longitude": float("nan")}, "INVALID_COORDINATES"),
        ({"latitude": 2.5, "longitude": ""}, "INVALID_COORDINATES"),
    ],
)
def test_quality_flags_invalid_or_missing_values(updates, expected_flag):
    result = assess_observation(sample(**updates))
    assert result["quality_status"] == "REVIEW"
    assert expected_flag in result["flags"]


@pytest.mark.parametrize(
    "updates,expected_flag",
    [
        ({"observation_date": "01/10/2026"}, "INVALID_DATE"),
        ({"observation_date": "2026-02-30"}, "INVALID_DATE"),
        ({"category": "Unapproved category"}, "INVALID_CATEGORY"),
        ({"severity": "Critical-ish"}, "INVALID_SEVERITY"),
        ({"status": "Auto-enforced"}, "INVALID_STATUS"),
        ({"latitude": True}, "INVALID_COORDINATES"),
        ({"longitude": False}, "INVALID_COORDINATES"),
    ],
)
def test_schema_and_coordinate_edge_cases_require_review(updates, expected_flag):
    result = assess_observation(sample(**updates))
    assert result["quality_status"] == "REVIEW"
    assert expected_flag in result["flags"]


def test_received_status_requires_review():
    result = assess_observation(sample(status="Received"))
    assert "NEEDS_REVIEW" in result["flags"]
    assert result["quality_status"] == "REVIEW"


def test_duplicate_comparison_handles_malformed_peer_fields_safely():
    result = assess_observation(
        sample(),
        peer_records=[
            {"case_id": "NA-OTHER", "district_or_site": None, "description": ["bad"]},
            {
                "case_id": "NA-OTHER2",
                "district_or_site": " pilot site a ",
                "category": "Water pollution",
                "observation_date": "2026-10-01",
                "description": "Synthetic observation of water discoloration",
            },
        ],
    )
    assert "DUPLICATE_SUSPECTED" in result["flags"]


@pytest.mark.parametrize("record", [None, [], "record", 7])
def test_non_mapping_record_fails_closed(record):
    with pytest.raises(ValueError, match="record must be a mapping"):
        assess_observation(record)


@pytest.mark.parametrize("peers", ["not-a-list", [None], [{"x": 1}, "bad"]])
def test_malformed_peer_collection_is_rejected(peers):
    with pytest.raises(ValueError, match="peer_records must be a sequence of mappings"):
        assess_observation(sample(), peer_records=peers)


def test_missing_consent_is_not_hidden_by_other_flags():
    result = assess_observation(sample(consent_confirmed=False, status="Received"))
    assert "MISSING_CONSENT" in result["flags"]
    assert "NEEDS_REVIEW" in result["flags"]
