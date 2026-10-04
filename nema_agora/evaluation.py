"""Evaluation and safety contracts for NEMA-AGORA Phase 9.

The benchmark layer is intentionally provider-neutral. It measures advisory
outputs against human-labelled fixtures and rejects autonomous-decision claims.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import json


SUPPORTED_CATEGORIES = (
    "Solid waste / illegal dumping",
    "Water pollution",
    "Wetland or land disturbance",
    "Biodiversity / wildlife observation",
    "Air / noise pollution",
    "Other environmental observation",
)


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    expected_category: str
    expected_duplicate: bool
    summary_faithful: bool | None = None

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id is required")
        if self.expected_category not in SUPPORTED_CATEGORIES:
            raise ValueError("Unsupported expected category")


@dataclass(frozen=True)
class EvaluationReport:
    category_accuracy: float
    duplicate_precision: float
    duplicate_recall: float
    duplicate_f1: float
    summary_faithfulness_rate: float | None
    cases_evaluated: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_category(cases: list[EvaluationCase], predictions: dict[str, str]) -> float:
    usable = [c for c in cases if c.case_id in predictions]
    if not usable:
        return 0.0
    return sum(predictions[c.case_id] == c.expected_category for c in usable) / len(usable)


def evaluate_duplicate(
    cases: list[EvaluationCase], predictions: dict[str, bool]
) -> tuple[float, float, float]:
    usable = [c for c in cases if c.case_id in predictions]
    tp = sum(predictions[c.case_id] and c.expected_duplicate for c in usable)
    fp = sum(predictions[c.case_id] and not c.expected_duplicate for c in usable)
    fn = sum((not predictions[c.case_id]) and c.expected_duplicate for c in usable)
    precision = _safe_ratio(tp, tp + fp)
    recall = _safe_ratio(tp, tp + fn)
    f1 = _safe_ratio(2 * precision * recall, precision + recall)
    return precision, recall, f1


def evaluate_summary_faithfulness(cases: list[EvaluationCase]) -> float | None:
    labels = [c.summary_faithful for c in cases if c.summary_faithful is not None]
    return _safe_ratio(sum(labels), len(labels)) if labels else None


def build_report(
    cases: list[EvaluationCase],
    category_predictions: dict[str, str],
    duplicate_predictions: dict[str, bool],
) -> EvaluationReport:
    precision, recall, f1 = evaluate_duplicate(cases, duplicate_predictions)
    return EvaluationReport(
        category_accuracy=evaluate_category(cases, category_predictions),
        duplicate_precision=precision,
        duplicate_recall=recall,
        duplicate_f1=f1,
        summary_faithfulness_rate=evaluate_summary_faithfulness(cases),
        cases_evaluated=len(cases),
    )


def validate_advisory_output(output: dict[str, Any]) -> list[str]:
    """Reject fields that would turn advisory AI into an autonomous decision engine."""
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


def serialise_report(report: EvaluationReport) -> str:
    return json.dumps(report.to_dict(), sort_keys=True, separators=(",", ":"))
