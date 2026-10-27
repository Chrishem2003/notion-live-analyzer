"""Phase 171 — release-readiness evidence contract tests."""
import copy
import hashlib
import json
import pytest

from nema_agora.release_readiness import (
    NOT_READY,
    READY_FOR_HUMAN_RELEASE_REVIEW,
    evaluate_release_readiness,
    validate_release_readiness_report,
)

SHA = "a" * 40
WHEN = "2026-10-10T11:00:00+03:00"
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


def evidence():
    return {
        gate: {
            "status": "PASS",
            "evidence_ref": f"artifact://release-check/{gate}",
            "verified_at": WHEN,
            "candidate_sha": SHA,
            "evidence_sha256": hashlib.sha256(f"synthetic-artifact:{gate}".encode("utf-8")).hexdigest(),
        }
        for gate in GATES
    }


def report(items=None):
    return evaluate_release_readiness(
        candidate_sha=SHA,
        evidence=evidence() if items is None else items,
        observed_at=WHEN,
    )


def test_all_required_gates_only_reach_human_review_ready_state():
    result = report()
    assert result["decision"] == READY_FOR_HUMAN_RELEASE_REVIEW
    assert result["passed_gate_count"] == 8
    assert result["release_approved"] is False
    assert result["production_ready"] is False
    assert result["execution_gate"] == "CLOSED"
    assert result["official_submission_performed"] is False
    assert validate_release_readiness_report(result) == result


@pytest.mark.parametrize("missing", list(GATES))
def test_each_missing_gate_fails_closed(missing):
    items = evidence()
    del items[missing]
    result = report(items)
    assert result["decision"] == NOT_READY
    assert result["gates"][missing] is False
    assert any(x["code"] == "MISSING_GATE_EVIDENCE" and x["gate"] == missing for x in result["findings"])


@pytest.mark.parametrize("bad_status", ["FAIL", "PENDING", "PASS_WITH_WARNINGS", None])
def test_non_pass_gate_does_not_count_as_pass(bad_status):
    items = evidence()
    items["focused_ci"]["status"] = bad_status
    result = report(items)
    assert result["decision"] == NOT_READY
    assert "GATE_NOT_PASSED" in {x["code"] for x in result["findings"]}


def test_evidence_must_be_bound_to_exact_release_candidate():
    items = evidence()
    items["focused_ci"]["candidate_sha"] = "b" * 40
    result = report(items)
    assert result["decision"] == NOT_READY
    assert "CANDIDATE_SHA_MISMATCH" in {x["code"] for x in result["findings"]}


def test_bad_timestamp_reference_and_sha_fail_closed():
    items = evidence()
    items["backup_restore_verification"]["verified_at"] = "yesterday"
    items["role_and_security_verification"]["evidence_ref"] = " "
    items["retention_verification"]["candidate_sha"] = "not-a-sha"
    items["evaluation_artifact_verification"]["evidence_sha256"] = "not-a-sha256"
    result = report(items)
    codes = {x["code"] for x in result["findings"]}
    assert {"INVALID_VERIFIED_AT", "INVALID_EVIDENCE_REFERENCE", "INVALID_EVIDENCE_CANDIDATE_SHA", "INVALID_EVIDENCE_SHA256"} <= codes
    assert result["decision"] == NOT_READY


def test_valid_evidence_digest_is_preserved_in_normalized_report():
    result = report()
    for gate in GATES:
        expected = hashlib.sha256(f"synthetic-artifact:{gate}".encode("utf-8")).hexdigest()
        assert result["normalized_evidence"][gate]["evidence_sha256"] == expected
    assert validate_release_readiness_report(result) == result


def test_unknown_gate_is_visible_and_blocks_readiness():
    items = evidence()
    items["focused_ci_typo"] = items.pop("focused_ci")
    result = report(items)
    codes = {x["code"] for x in result["findings"]}
    assert "UNRECOGNIZED_GATE_EVIDENCE" in codes
    assert result["decision"] == NOT_READY


@pytest.mark.parametrize("sha", ["", "abc", "g" * 40, "a" * 41])
def test_invalid_candidate_sha_is_rejected(sha):
    with pytest.raises(ValueError, match="INVALID_CANDIDATE_SHA"):
        evaluate_release_readiness(candidate_sha=sha, evidence=evidence(), observed_at=WHEN)


def test_fingerprint_detects_report_tampering():
    result = report()
    changed = copy.deepcopy(result)
    changed["release_approved"] = True
    with pytest.raises(ValueError, match="READINESS_FINGERPRINT_MISMATCH"):
        validate_release_readiness_report(changed)


def _resign(report_value):
    payload = dict(report_value)
    payload.pop("readiness_fingerprint", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    payload["readiness_fingerprint"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return payload


def test_report_validator_rejects_execution_gate_open_even_with_recomputed_fingerprint():
    result = report()
    result["execution_gate"] = "OPEN"
    with pytest.raises(ValueError, match="EXECUTION_GATE_MUST_REMAIN_CLOSED"):
        validate_release_readiness_report(_resign(result))


def test_report_validator_rejects_forged_production_approval_even_with_valid_fingerprint():
    result = report()
    result["production_ready"] = True
    with pytest.raises(ValueError, match="UNSUPPORTED_RELEASE_CLAIM"):
        validate_release_readiness_report(_resign(result))


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("official_nema_integration", True, "OFFICIAL_INTEGRATION_CLAIM_FORBIDDEN"),
        ("official_submission_performed", True, "OFFICIAL_SUBMISSION_CLAIM_FORBIDDEN"),
        ("automatic_deployment_performed", True, "AUTOMATIC_DEPLOYMENT_CLAIM_FORBIDDEN"),
        ("environmental_conclusion", "COMPLIANT", "ENVIRONMENTAL_CONCLUSION_FORBIDDEN"),
        ("regulatory_conclusion", "APPROVED", "REGULATORY_CONCLUSION_FORBIDDEN"),
        ("enforcement_action", "ISSUED", "ENFORCEMENT_ACTION_FORBIDDEN"),
    ],
)
def test_report_validator_rejects_forged_safety_claims_even_with_valid_fingerprint(field, value, error):
    result = report()
    result[field] = value
    with pytest.raises(ValueError, match=error):
        validate_release_readiness_report(_resign(result))


def test_invalid_observation_time_and_non_mapping_evidence_rejected():
    with pytest.raises(ValueError, match="INVALID_OBSERVED_AT"):
        evaluate_release_readiness(candidate_sha=SHA, evidence=evidence(), observed_at="not-time")
    with pytest.raises(ValueError, match="EVIDENCE_MAPPING_REQUIRED"):
        evaluate_release_readiness(candidate_sha=SHA, evidence=[], observed_at=WHEN)

def test_report_validator_rejects_inconsistent_gate_count_even_with_valid_fingerprint():
    result = report()
    result["passed_gate_count"] = 0
    with pytest.raises(ValueError, match="PASSED_GATE_COUNT_MISMATCH"):
        validate_release_readiness_report(_resign(result))


def test_report_validator_rejects_re_signed_inconsistent_decision():
    result = report()
    result["decision"] = NOT_READY
    with pytest.raises(ValueError, match="READINESS_DECISION_INCONSISTENT"):
        validate_release_readiness_report(_resign(result))


def test_report_validator_rejects_missing_normalized_gate_evidence():
    result = report()
    result["normalized_evidence"].pop("focused_ci")
    with pytest.raises(ValueError, match="NORMALIZED_EVIDENCE_GATE_MISMATCH"):
        validate_release_readiness_report(_resign(result))


def test_report_validator_rejects_wrong_candidate_in_normalized_evidence():
    result = report()
    result["normalized_evidence"]["focused_ci"]["candidate_sha"] = "b" * 40
    with pytest.raises(ValueError, match="NORMALIZED_EVIDENCE_CANDIDATE_MISMATCH"):
        validate_release_readiness_report(_resign(result))


def test_report_validator_rejects_invalid_candidate_and_observation_time_when_resigned():
    result = report()
    result["candidate_sha"] = "not-a-sha"
    with pytest.raises(ValueError, match="INVALID_REPORT_CANDIDATE_SHA"):
        validate_release_readiness_report(_resign(result))
    result = report()
    result["observed_at"] = "yesterday"
    with pytest.raises(ValueError, match="INVALID_REPORT_OBSERVED_AT"):
        validate_release_readiness_report(_resign(result))


def test_future_dated_evidence_fails_closed():
    items = evidence()
    items["focused_ci"]["verified_at"] = "2026-10-10T11:00:01+03:00"
    result = evaluate_release_readiness(
        candidate_sha=SHA,
        evidence=items,
        observed_at=WHEN,
    )
    assert result["decision"] == NOT_READY
    assert {"code": "EVIDENCE_VERIFIED_AFTER_ASSESSMENT", "gate": "focused_ci"} in result["findings"]


def test_lowercase_z_timestamp_is_supported_without_global_replacement():
    items = evidence()
    items["focused_ci"]["verified_at"] = "2026-10-10T08:00:00z"
    result = evaluate_release_readiness(
        candidate_sha=SHA,
        evidence=items,
        observed_at="2026-10-10T08:00:00Z",
    )
    assert result["gates"]["focused_ci"] is True


def test_resigned_report_cannot_smuggle_future_dated_evidence():
    result = report()
    result["normalized_evidence"]["focused_ci"]["verified_at"] = "2026-10-10T11:00:01+03:00"
    with pytest.raises(ValueError, match="NORMALIZED_EVIDENCE_AFTER_ASSESSMENT"):
        validate_release_readiness_report(_resign(result))
