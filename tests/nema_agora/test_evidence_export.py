from copy import deepcopy

from nema_agora.evidence_case import (
    EvidenceReference,
    attach_human_review,
    build_evidence_case,
    mark_exported,
)
from nema_agora.evidence_export import (
    build_export_package,
    export_json,
    verify_export_package,
)


def reviewed_exported_case():
    case = build_evidence_case(
        case_id="c1",
        observation={"site_ref": "pilot", "measurement": 1},
        evidence=[
            EvidenceReference(
                "e1", "photo", "pilot", "2026-10-04T12:00:00+00:00", "fp"
            )
        ],
        created_at="2026-10-04T11:00:00+00:00",
    )
    reviewed = attach_human_review(
        case,
        reviewer_id="r1",
        role="coordinator",
        decision="ACKNOWLEDGED",
        reviewed_at="2026-10-04T12:10:00+00:00",
    )
    return mark_exported(reviewed)


def test_export_package_is_non_submission_and_verifiable():
    package = build_export_package(reviewed_exported_case())
    assert package["official_submission"] is False
    assert package["execution_gate"] == "CLOSED"
    result = verify_export_package(package)
    assert result["valid"] is True
    assert result["case_id"] == "c1"
    assert result["source_authenticity_verified"] is False
    assert result["nema_authorization_verified"] is False


def test_offline_verifier_detects_tampered_evidence_even_if_embedded_validation_is_unchanged():
    package = build_export_package(reviewed_exported_case())
    tampered = deepcopy(package)
    tampered["case"]["evidence"][0]["source"] = "changed-source"
    result = verify_export_package(tampered)
    assert result["valid"] is False
    assert "case:provenance_fingerprint_mismatch" in result["issues"]


def test_offline_verifier_detects_tampered_review_and_embedded_claims():
    package = build_export_package(reviewed_exported_case())
    tampered = deepcopy(package)
    tampered["case"]["review"]["decision"] = "ESCALATED"
    tampered["official_submission"] = True
    tampered["execution_gate"] = "OPEN"
    result = verify_export_package(tampered)
    assert result["valid"] is False
    assert "case:review_fingerprint_mismatch" in result["issues"]
    assert "official_submission_flag_must_be_false" in result["issues"]
    assert "execution_gate_must_remain_closed" in result["issues"]


def test_offline_verifier_rejects_forged_embedded_validation_and_wrong_state():
    package = build_export_package(reviewed_exported_case())
    tampered = deepcopy(package)
    tampered["validation"]["valid"] = False
    tampered["case"]["state"] = "READY_FOR_REVIEW"
    result = verify_export_package(tampered)
    assert result["valid"] is False
    assert "embedded_validation_mismatch:valid" in result["issues"]
    assert "case_not_human_reviewed_and_exported" in result["issues"]


def test_offline_verifier_fails_closed_for_malformed_packages():
    assert verify_export_package(None)["valid"] is False
    assert "unsupported_schema" in verify_export_package({})["issues"]


def test_export_json_is_deterministic_and_newline_terminated():
    case = reviewed_exported_case()
    assert export_json(case) == export_json(case)
    assert export_json(case).endswith("\n")
