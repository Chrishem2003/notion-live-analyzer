"""Focused contract tests for the NEMA-AGORA pilot's safety-critical helpers."""
from datetime import date

import pytest

from nema_agora.access import can_read_observation, has_permission
from nema_agora.core import (
    CATEGORIES,
    SEVERITIES,
    csv_safe_value,
    make_observation,
    normalise_coordinates,
    validate_observation,
)
from nema_agora.governance import DEFAULT_SCOPE, validate_governance
from nema_agora.release_readiness import (
    NOT_READY,
    READY_FOR_HUMAN_RELEASE_REVIEW,
    evaluate_release_readiness,
    validate_release_readiness_report,
)

CANDIDATE_SHA = "b" * 40
OBSERVED_AT = "2026-10-18T09:00:00+03:00"
GATES = (
    "focused_ci",
    "clean_environment_end_to_end",
    "role_and_security_verification",
    "backup_restore_verification",
    "retention_verification",
    "evaluation_artifact_verification",
    "accessibility_and_data_governance_review",
    "institutional_approval",
)


def _complete_evidence():
    return {
        gate: {
            "status": "PASS",
            "evidence_ref": f"evidence/{gate}",
            "verified_at": "2026-10-18T08:00:00+03:00",
            "candidate_sha": CANDIDATE_SHA,
            "evidence_sha256": "a" * 64,
        }
        for gate in GATES
    }


def test_observation_validation_reports_missing_required_inputs():
    errors = validate_observation(site=" ", description="", consent_confirmed=False)
    assert any("site label" in error for error in errors)
    assert any("description" in error for error in errors)
    assert any("Permission" in error for error in errors)


def test_observation_rejects_unknown_category_and_out_of_range_coordinates():
    with pytest.raises(ValueError, match="Unknown observation category"):
        make_observation(
            observation_date=date(2026, 10, 18),
            category="Invented category",
            severity=SEVERITIES[0],
            site="Gulu",
            description="Synthetic pilot observation",
            latitude=2.7,
            longitude=32.3,
            consent_confirmed=True,
            created_at=OBSERVED_AT,
        )
    with pytest.raises(ValueError, match="Latitude"):
        normalise_coordinates(91, 32)


def test_zero_coordinate_pair_is_treated_as_omitted_and_valid_record_is_bounded():
    assert normalise_coordinates(0.0, 0.0) is None
    record = make_observation(
        observation_date=date(2026, 10, 18),
        category=CATEGORIES[0],
        severity=SEVERITIES[0],
        site="  Gulu  ",
        description="  Synthetic pilot observation  ",
        latitude=0.0,
        longitude=0.0,
        consent_confirmed=True,
        created_at=OBSERVED_AT,
    )
    assert record["district_or_site"] == "Gulu"
    assert record["description"] == "Synthetic pilot observation"
    assert record["latitude"] == record["longitude"] == ""
    assert record["status"] == "Received"


@pytest.mark.parametrize("value", ["=1+1", "  +SUM(A1:A2)", "-cmd", "@formula", "\tformula"])
def test_csv_export_neutralises_spreadsheet_formula_prefixes(value):
    assert csv_safe_value(value).startswith("'")
    assert csv_safe_value(-12.3) == -12.3


def test_permissions_fail_closed_for_unknown_roles_and_permissions():
    assert not has_permission("unknown-role", "observation:read_all")
    assert not has_permission("admin", "invented:permission")
    assert can_read_observation("submitter", "actor-a", "actor-a")
    assert not can_read_observation("submitter", "actor-a", "actor-b")
    assert can_read_observation("reviewer", "actor-a", "actor-b")


def test_default_governance_policy_is_valid_and_unsafe_overrides_are_blocked():
    assert validate_governance(DEFAULT_SCOPE) == []
    unsafe = dict(DEFAULT_SCOPE, allow_personal_data=True)
    assert any("Personal-data collection is blocked" in error for error in validate_governance(unsafe))
    urgent = dict(DEFAULT_SCOPE, allow_urgent_incidents=True)
    assert any("Urgent incident intake" in error for error in validate_governance(urgent))


def test_release_readiness_fails_closed_when_gate_evidence_is_missing():
    report = evaluate_release_readiness(
        candidate_sha=CANDIDATE_SHA,
        evidence={},
        observed_at=OBSERVED_AT,
    )
    assert report["decision"] == NOT_READY
    assert report["passed_gate_count"] == 0
    assert report["execution_gate"] == "CLOSED"
    assert report["release_approved"] is False
    assert report["production_ready"] is False
    assert validate_release_readiness_report(report)["decision"] == NOT_READY


def test_release_readiness_requires_evidence_bound_to_exact_candidate():
    evidence = _complete_evidence()
    evidence["focused_ci"]["candidate_sha"] = "c" * 40
    report = evaluate_release_readiness(
        candidate_sha=CANDIDATE_SHA,
        evidence=evidence,
        observed_at=OBSERVED_AT,
    )
    assert report["decision"] == NOT_READY
    assert any(item["code"] == "CANDIDATE_SHA_MISMATCH" for item in report["findings"])


def test_complete_candidate_bound_evidence_only_unlocks_human_review():
    report = evaluate_release_readiness(
        candidate_sha=CANDIDATE_SHA,
        evidence=_complete_evidence(),
        observed_at=OBSERVED_AT,
    )
    assert report["decision"] == READY_FOR_HUMAN_RELEASE_REVIEW
    assert report["passed_gate_count"] == len(GATES)
    assert report["release_approved"] is False
    assert report["production_ready"] is False
    assert report["official_nema_integration"] is False
    assert report["official_submission_performed"] is False
    assert report["automatic_deployment_performed"] is False
    assert validate_release_readiness_report(report) == report


def test_release_readiness_report_rejects_tampering():
    report = evaluate_release_readiness(
        candidate_sha=CANDIDATE_SHA,
        evidence=_complete_evidence(),
        observed_at=OBSERVED_AT,
    )
    report["production_ready"] = True
    with pytest.raises(ValueError, match="READINESS_FINGERPRINT_MISMATCH"):
        validate_release_readiness_report(report)
