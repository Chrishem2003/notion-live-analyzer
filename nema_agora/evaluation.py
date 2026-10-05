"""Reproducible evaluation primitives for NEMA-AGORA advisory systems."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json
import math
import re

POLICY_VERSION = "evaluation-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _fp(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    input_fingerprint: str
    expected_label: str
    observed_label: str
    model_id: str
    model_version: str


@dataclass(frozen=True)
class EvaluationRun:
    run_id: str
    dataset_fingerprint: str
    cases: tuple[EvaluationCase, ...]
    accuracy: float
    policy_version: str = POLICY_VERSION


def _validate_case_fields(case: EvaluationCase) -> list[str]:
    issues: list[str] = []
    if not case.case_id.strip():
        issues.append("missing_case_id")
    if not case.input_fingerprint.strip():
        issues.append("missing_input_fingerprint")
    if not case.expected_label.strip():
        issues.append("missing_expected_label")
    if not case.observed_label.strip():
        issues.append("missing_observed_label")
    if not case.model_id.strip():
        issues.append("missing_model_id")
    if not case.model_version.strip():
        issues.append("missing_model_version")
    return issues


def build_evaluation_run(
    *,
    run_id: str,
    dataset: Mapping[str, Any],
    cases: list[EvaluationCase] | tuple[EvaluationCase, ...],
) -> EvaluationRun:
    if not run_id.strip():
        raise ValueError("run_id is required")
    items = tuple(cases)
    if not items:
        raise ValueError("at least one evaluation case is required")
    if len({c.case_id for c in items}) != len(items):
        raise ValueError("case_id values must be unique")
    for case in items:
        issues = _validate_case_fields(case)
        if issues:
            raise ValueError(f"invalid evaluation case: {issues[0]}")
    accuracy = sum(c.expected_label == c.observed_label for c in items) / len(items)
    return EvaluationRun(run_id, _fp(dataset), items, accuracy)


def evaluation_run_fingerprint(run: EvaluationRun) -> str:
    """Return a deterministic artifact identity derived from the complete run."""
    return _fp(
        {
            "policy_version": run.policy_version,
            "run_id": run.run_id,
            "dataset_fingerprint": run.dataset_fingerprint,
            "cases": [
                {
                    "case_id": c.case_id,
                    "input_fingerprint": c.input_fingerprint,
                    "expected_label": c.expected_label,
                    "observed_label": c.observed_label,
                    "model_id": c.model_id,
                    "model_version": c.model_version,
                }
                for c in run.cases
            ],
            "accuracy": run.accuracy,
        }
    )


def validate_evaluation_run(run: EvaluationRun) -> dict[str, Any]:
    issues: list[str] = []
    if not run.run_id.strip() or not run.dataset_fingerprint.strip():
        issues.append("missing_identity")
    if run.policy_version != POLICY_VERSION:
        issues.append("unsupported_policy_version")
    if not run.cases:
        issues.append("empty_cases")
    if not math.isfinite(run.accuracy) or not 0 <= run.accuracy <= 1:
        issues.append("invalid_accuracy")
    expected_accuracy = (
        sum(c.expected_label == c.observed_label for c in run.cases) / len(run.cases)
        if run.cases
        else 0.0
    )
    if run.accuracy != expected_accuracy:
        issues.append("accuracy_mismatch")
    case_ids = [c.case_id for c in run.cases]
    if len(set(case_ids)) != len(case_ids):
        issues.append("duplicate_case_id")
    for case in run.cases:
        issues.extend(f"{case.case_id}:{issue}" for issue in _validate_case_fields(case))
        if case.input_fingerprint and not _SHA256_RE.fullmatch(case.input_fingerprint):
            issues.append(f"{case.case_id}:invalid_input_fingerprint")
    return {
        "policy_version": POLICY_VERSION,
        "run_id": run.run_id,
        "valid": not issues,
        "issues": issues,
        "reproducible": not issues,
        "artifact_fingerprint": evaluation_run_fingerprint(run),
        "advisory_evaluation_only": True,
        "human_governed": True,
        "automatic_model_admission": False,
        "regulatory_conclusion": False,
    }


# Compatibility contract retained for the Phase 9/15 advisory pipeline.
SUPPORTED_CATEGORIES = (
    "Solid waste / illegal dumping",
    "Water pollution",
    "Wetland or land disturbance",
    "Biodiversity / wildlife observation",
    "Air / noise pollution",
    "Other environmental observation",
)


def validate_advisory_output(output: dict[str, Any]) -> list[str]:
    """Reject output fields that would cross the advisory-only safety boundary."""
    errors: list[str] = []
    forbidden = {
        "enforcement_action",
        "regulatory_decision",
        "official_incident_status",
        "automatic_workflow_transition",
        "emergency_dispatch",
    }
    for key in forbidden:
        if key in output:
            errors.append(f"Forbidden autonomous field: {key}")
    if output.get("human_review_required") is not True:
        errors.append("human_review_required must be True")
    if not isinstance(output.get("source_case_id"), str) or not output["source_case_id"].strip():
        errors.append("source_case_id is required")
    return errors
