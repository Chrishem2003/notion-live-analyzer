"""Phase 171 — fail-closed release-candidate readiness evidence gate.

This evaluates evidence completeness for a human release review. It never deploys,
submits to an authority, enables execution, or declares production approval.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re
from typing import Any, Mapping

POLICY_VERSION = "phase171-v1"
READY_FOR_HUMAN_RELEASE_REVIEW = "READY_FOR_HUMAN_RELEASE_REVIEW"
NOT_READY = "NOT_READY"
_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_REQUIRED_GATES = (
    "focused_ci",
    "clean_environment_end_to_end",
    "role_and_security_verification",
    "backup_restore_verification",
    "retention_verification",
    "evaluation_artifact_verification",
    "accessibility_and_data_governance_review",
    "institutional_approval",
)


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def evaluate_release_readiness(
    *,
    candidate_sha: str,
    evidence: Mapping[str, Any],
    observed_at: str,
) -> dict[str, Any]:
    """Validate evidence coverage, freshness binding and exact candidate identity.

    Each required evidence entry must contain status='PASS', a non-empty evidence
    reference, an offset-aware ISO timestamp, and candidate_sha matching the
    exact release candidate. Missing or malformed evidence always fails closed.
    """
    if not isinstance(candidate_sha, str) or not _SHA_RE.fullmatch(candidate_sha):
        raise ValueError("INVALID_CANDIDATE_SHA")
    candidate_sha = candidate_sha.lower()
    if not _valid_timestamp(observed_at):
        raise ValueError("INVALID_OBSERVED_AT")
    if not isinstance(evidence, Mapping):
        raise ValueError("EVIDENCE_MAPPING_REQUIRED")

    gates: dict[str, bool] = {}
    findings: list[dict[str, str]] = []
    normalized: dict[str, dict[str, str]] = {}

    for gate in _REQUIRED_GATES:
        item = evidence.get(gate)
        if not isinstance(item, Mapping):
            gates[gate] = False
            findings.append({"code": "MISSING_GATE_EVIDENCE", "gate": gate})
            continue

        status = item.get("status")
        reference = item.get("evidence_ref")
        verified_at = item.get("verified_at")
        bound_sha = item.get("candidate_sha")
        issues: list[str] = []
        if status != "PASS":
            issues.append("GATE_NOT_PASSED")
        if not isinstance(reference, str) or not reference.strip() or len(reference) > 2048:
            issues.append("INVALID_EVIDENCE_REFERENCE")
        if not _valid_timestamp(verified_at):
            issues.append("INVALID_VERIFIED_AT")
        if not isinstance(bound_sha, str) or not _SHA_RE.fullmatch(bound_sha):
            issues.append("INVALID_EVIDENCE_CANDIDATE_SHA")
        elif bound_sha.lower() != candidate_sha:
            issues.append("CANDIDATE_SHA_MISMATCH")

        gates[gate] = not issues
        if issues:
            findings.extend({"code": code, "gate": gate} for code in issues)
        else:
            normalized[gate] = {
                "status": "PASS",
                "evidence_ref": reference.strip(),
                "verified_at": verified_at.strip(),
                "candidate_sha": bound_sha.lower(),
            }

    # Unexpected keys are reported so misspelled or obsolete gate names are visible.
    for extra in sorted(str(key) for key in evidence.keys() if key not in _REQUIRED_GATES):
        findings.append({"code": "UNRECOGNIZED_GATE_EVIDENCE", "gate": extra})

    findings.sort(key=lambda row: (row["gate"], row["code"]))
    passed = sum(gates.values())
    decision = READY_FOR_HUMAN_RELEASE_REVIEW if passed == len(_REQUIRED_GATES) and not findings else NOT_READY
    payload = {
        "policy_version": POLICY_VERSION,
        "candidate_sha": candidate_sha,
        "observed_at": observed_at.strip(),
        "decision": decision,
        "gate_count": len(_REQUIRED_GATES),
        "passed_gate_count": passed,
        "gates": gates,
        "findings": findings,
        "normalized_evidence": normalized,
        "release_approved": False,
        "production_ready": False,
        "official_nema_integration": False,
        "official_submission_performed": False,
        "execution_gate": "CLOSED",
        "automatic_deployment_performed": False,
        "environmental_conclusion": None,
        "regulatory_conclusion": None,
        "enforcement_action": None,
        "human_release_review_required": True,
    }
    return dict(payload, readiness_fingerprint=_digest(payload))


def validate_release_readiness_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute report fingerprint and reject claims outside the readiness contract."""
    if not isinstance(report, Mapping):
        raise ValueError("REPORT_MAPPING_REQUIRED")
    claimed = report.get("readiness_fingerprint")
    if not isinstance(claimed, str) or not _SHA_RE.fullmatch(claimed):
        raise ValueError("INVALID_READINESS_FINGERPRINT")
    payload = dict(report)
    payload.pop("readiness_fingerprint", None)
    if _digest(payload) != claimed:
        raise ValueError("READINESS_FINGERPRINT_MISMATCH")
    if payload.get("policy_version") != POLICY_VERSION:
        raise ValueError("INVALID_POLICY_VERSION")
    if payload.get("decision") not in (READY_FOR_HUMAN_RELEASE_REVIEW, NOT_READY):
        raise ValueError("INVALID_READINESS_DECISION")
    if payload.get("release_approved") is not False or payload.get("production_ready") is not False:
        raise ValueError("UNSUPPORTED_RELEASE_CLAIM")
    if payload.get("execution_gate") != "CLOSED":
        raise ValueError("EXECUTION_GATE_MUST_REMAIN_CLOSED")
    if payload.get("human_release_review_required") is not True:
        raise ValueError("HUMAN_RELEASE_REVIEW_REQUIRED")
    return dict(report)
