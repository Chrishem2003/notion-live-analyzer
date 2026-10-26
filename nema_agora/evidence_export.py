"""Deterministic local export packaging and offline verification for NEMA-AGORA cases."""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .evidence_case import (
    EvidenceCase,
    evidence_case_from_dict,
    validate_evidence_case,
)


def build_export_package(case: EvidenceCase) -> dict[str, Any]:
    validation = validate_evidence_case(case)
    if not validation["valid"]:
        raise ValueError("cannot export invalid case")
    if case.state != "EXPORTED" or case.review is None:
        raise ValueError("case must be human-reviewed before export")
    return {
        "schema": "nema-agora-evidence-package-v1",
        "case": case.to_dict(),
        "validation": validation,
        "official_submission": False,
        "environmental_truth_claim": False,
        "regulatory_conclusion": False,
        "execution_gate": "CLOSED",
    }


def verify_export_package(package: Any) -> dict[str, Any]:
    """Verify an exported JSON-compatible package without trusting its embedded validation.

    This confirms package structure and internal fingerprints only. It does not
    prove the source evidence is authentic, the observations are true, or the
    package was issued by NEMA.
    """
    issues: list[str] = []
    if not isinstance(package, Mapping):
        return {
            "valid": False,
            "issues": ["invalid_package_type"],
            "execution_gate": "CLOSED",
            "official_submission": False,
            "environmental_truth_claim": False,
            "regulatory_conclusion": False,
        }

    if package.get("schema") != "nema-agora-evidence-package-v1":
        issues.append("unsupported_schema")
    if package.get("official_submission") is not False:
        issues.append("official_submission_flag_must_be_false")
    if package.get("environmental_truth_claim") is not False:
        issues.append("environmental_truth_claim_flag_must_be_false")
    if package.get("regulatory_conclusion") is not False:
        issues.append("regulatory_conclusion_flag_must_be_false")
    if package.get("execution_gate") != "CLOSED":
        issues.append("execution_gate_must_remain_closed")

    try:
        case_payload = package.get("case")
        case = evidence_case_from_dict(case_payload)
        actual_validation = validate_evidence_case(case)
        if not actual_validation["valid"]:
            issues.extend(f"case:{issue}" for issue in actual_validation["issues"])
        if case.state != "EXPORTED" or case.review is None:
            issues.append("case_not_human_reviewed_and_exported")

        embedded = package.get("validation")
        if not isinstance(embedded, Mapping):
            issues.append("embedded_validation_missing")
        else:
            # Embedded validation is informational only; never use it instead
            # of the independently recomputed result above.
            for key in ("valid", "case_id", "state", "execution_gate"):
                if embedded.get(key) != actual_validation.get(key):
                    issues.append(f"embedded_validation_mismatch:{key}")
            if embedded.get("valid") is not True:
                issues.append("embedded_validation_not_valid")
            if embedded.get("execution_gate") != "CLOSED":
                issues.append("embedded_execution_gate_must_remain_closed")
    except (TypeError, ValueError, KeyError):
        issues.append("case_schema_invalid")

    return {
        "valid": not issues,
        "issues": sorted(set(issues)),
        "case_id": case.case_id if "case" in locals() else None,
        "state": case.state if "case" in locals() else None,
        "execution_gate": "CLOSED",
        "official_submission": False,
        "environmental_truth_claim": False,
        "regulatory_conclusion": False,
        "source_authenticity_verified": False,
        "nema_authorization_verified": False,
    }


def export_json(case: EvidenceCase) -> str:
    return json.dumps(
        build_export_package(case),
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"
