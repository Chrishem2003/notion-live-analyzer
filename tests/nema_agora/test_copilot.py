from datetime import date

import pytest

from nema_agora.copilot import COPILOT_VERSION, build_reviewer_copilot
from nema_agora.intelligence import analyze_observation
from nema_agora.core import CATEGORIES, make_observation


def record():
    return make_observation(
        observation_date=date(2026, 10, 4),
        category=CATEGORIES[0],
        severity="Moderate",
        site="Pilot A",
        description="Synthetic waste observation near a drainage channel",
        latitude=2.5,
        longitude=32.1,
        consent_confirmed=True,
        created_at="2026-10-04T12:00:00+03:00",
    )


def test_copilot_is_bound_to_source_case_and_version():
    rec = record()
    analysis = analyze_observation(rec, peer_records=[])
    result = build_reviewer_copilot(rec, analysis)
    assert result["source_case_id"] == rec["case_id"]
    assert result["copilot_version"] == COPILOT_VERSION
    assert result["human_review_required"] is True


def test_copilot_uses_only_supplied_evidence():
    rec = record()
    analysis = analyze_observation(rec, peer_records=[])
    result = build_reviewer_copilot(rec, analysis)
    values = " ".join(item["value"] for item in result["evidence_facts"])
    assert "drainage" in values
    assert "confirmed illegal dumping" not in values
    assert "NEMA has verified" not in values


def test_copilot_surfaces_duplicate_review_question():
    rec = record()
    peer = dict(rec)
    peer["case_id"] = "CASE-PEER"
    analysis = analyze_observation(rec, peer_records=[peer])
    result = build_reviewer_copilot(rec, analysis)
    assert result["duplicate_review"]["candidate_case_ids"] == ["CASE-PEER"]
    assert any("candidate" in question.lower() for question in result["uncertainty_questions"])


def test_copilot_rejects_missing_case_id():
    analysis = {"quality_status": "REVIEW", "quality_flags": []}
    with pytest.raises(ValueError):
        build_reviewer_copilot({"description": "x"}, analysis)
