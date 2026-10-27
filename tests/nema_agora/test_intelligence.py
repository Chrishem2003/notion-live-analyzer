from nema_agora.core import CATEGORIES
from nema_agora.intelligence import (
    analyze_observation,
    duplicate_candidates,
    priority_advisory,
    suggest_categories,
    summarize_observation,
)


def base(**overrides):
    record = {
        "case_id": "NA-1",
        "observation_date": "2026-10-04",
        "category": CATEGORIES[0],
        "severity": "Moderate",
        "district_or_site": "Pilot A",
        "description": "Visible plastic waste and garbage near drainage channel",
        "latitude": 2.5,
        "longitude": 32.1,
        "status": "Under review",
        "consent_confirmed": True,
    }
    record.update(overrides)
    return record


def test_summary_is_extractively_bounded():
    result = summarize_observation(base(description="one " * 300), max_chars=100)
    assert len(result) <= 100
    assert result.endswith("…")


def test_category_suggestions_are_explainable():
    result = suggest_categories(base())
    assert result[0]["category"] == "Solid waste / illegal dumping"
    assert "waste" in result[0]["matched_terms"]


def test_duplicate_candidates_return_matching_case_ids():
    peer = base(case_id="NA-2")
    assert duplicate_candidates(base(), [peer]) == ["NA-2"]


def test_priority_advisory_never_promotes_invalid_data():
    result = analyze_observation(base(description=""))
    assert result["priority_advisory"]["level"] == "REVIEW"
    assert result["human_review_required"] is True


def test_urgent_scope_is_blocked_from_priority_claims():
    result = analyze_observation(base(severity="Urgent"))
    assert result["priority_advisory"]["level"] == "BLOCKED_BY_SCOPE"


def test_analysis_contains_decision_safety_notice():
    result = analyze_observation(base())
    assert "does not establish environmental truth" in result["decision_notice"]
