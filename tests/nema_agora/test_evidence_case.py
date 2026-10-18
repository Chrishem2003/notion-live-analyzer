from dataclasses import replace

import pytest

from nema_agora.evidence_case import *


def make_case():
    ref = EvidenceReference(
        "img-1", "image", "pilot-upload",
        "2026-10-04T12:00:00+00:00", "abc123"
    )
    finding = AdvisoryFinding(
        "finding-1", "pilot-model", "1",
        "Advisory observation requiring human review", 0.72,
        ("abc123",), "2026-10-04T12:01:00+00:00"
    )
    return build_evidence_case(
        case_id="case-001",
        observation={"site_ref": "pilot-site", "measurement": 42},
        evidence=[ref],
        findings=[finding],
        created_at="2026-10-04T12:02:00+00:00",
    )


def test_build_is_reviewable_and_provenance_bound():
    case = make_case()
    assert case.state == "READY_FOR_REVIEW"
    assert len(case.provenance_fingerprint) == 64
    assert validate_evidence_case(case)["valid"] is True


def test_review_then_export_requires_human_decision():
    reviewed = attach_human_review(
        make_case(), reviewer_id="reviewer-1", role="coordinator",
        decision="ACKNOWLEDGED"
    )
    assert validate_evidence_case(reviewed)["valid"] is True
    assert mark_exported(reviewed).state == "EXPORTED"


def test_export_without_review_is_blocked():
    with pytest.raises(ValueError, match="human-reviewed"):
        mark_exported(make_case())


def test_non_advisory_finding_is_rejected():
    finding = AdvisoryFinding(
        "f", "m", "1", "x", 0.5, (), "2026-10-04T12:00:00+00:00", False
    )
    with pytest.raises(ValueError, match="advisory_only"):
        build_evidence_case(case_id="case-002", observation={"x": 1}, evidence=[], findings=[finding])


def test_tampered_evidence_invalidates_provenance():
    case = make_case()
    tampered_reference = replace(case.evidence[0], source="different-source")
    tampered = replace(case, evidence=(tampered_reference,))
    result = validate_evidence_case(tampered)
    assert result["valid"] is False
    assert "provenance_fingerprint_mismatch" in result["issues"]
    with pytest.raises(ValueError, match="integrity validation"):
        mark_exported(replace(tampered, state="REVIEWED", review=HumanReview(
            "reviewer-1", "coordinator", "ACKNOWLEDGED", "2026-10-04T12:03:00+00:00"
        )))


def test_naive_timestamps_are_rejected():
    with pytest.raises(ValueError, match="timezone"):
        build_evidence_case(
            case_id="case-003", observation={"x": 1}, evidence=[],
            created_at="2026-10-04T12:02:00"
        )


def test_invalid_review_decision_fails_closed():
    case = make_case()
    malformed_review = HumanReview(
        "reviewer-1", "coordinator", "APPROVED_BY_AI",
        "2026-10-04T12:03:00+00:00"
    )
    result = validate_evidence_case(replace(
        case, state="REVIEWED", review=malformed_review
    ))
    assert result["valid"] is False
    assert "invalid_review_decision" in result["issues"]

def test_tampered_human_review_invalidates_review_fingerprint():
    case = attach_human_review(
        make_case(), reviewer_id="reviewer-1", role="coordinator",
        decision="ACKNOWLEDGED", reviewed_at="2026-10-04T12:03:00+00:00"
    )
    tampered_review = replace(case.review, decision="ESCALATED")
    tampered = replace(case, review=tampered_review)
    result = validate_evidence_case(tampered)
    assert result["valid"] is False
    assert "review_fingerprint_mismatch" in result["issues"]
    with pytest.raises(ValueError, match="integrity validation"):
        mark_exported(tampered)

def test_builder_rejects_evidence_without_timezone():
    bad_reference = EvidenceReference(
        "img-bad", "image", "pilot-upload",
        "2026-10-04T12:00:00", "abc123"
    )
    with pytest.raises(ValueError, match="captured_at"):
        build_evidence_case(
            case_id="case-bad-evidence", observation={"site_ref": "pilot-site"},
            evidence=[bad_reference]
        )


def test_builder_rejects_non_json_observation_and_metadata():
    with pytest.raises(ValueError, match="JSON serializable"):
        build_evidence_case(
            case_id="case-bad-observation", observation={"not_json": object()},
            evidence=[]
        )
    bad_reference = EvidenceReference(
        "img-bad-meta", "image", "pilot-upload",
        "2026-10-04T12:00:00+00:00", "abc123", {"bad": object()}
    )
    with pytest.raises(ValueError, match="metadata"):
        build_evidence_case(
            case_id="case-bad-metadata", observation={"site_ref": "pilot-site"},
            evidence=[bad_reference]
        )

def test_builder_rejects_non_finite_json_numbers():
    with pytest.raises(ValueError, match="JSON serializable"):
        build_evidence_case(
            case_id="case-nan", observation={"measurement": float("nan")},
            evidence=[]
        )
