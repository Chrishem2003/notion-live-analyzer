"""Phase 11 pilot intelligence observatory.

Turns reviewer feedback and evaluation reports into transparent readiness
signals. This module measures the system; it never authorises deployment.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from nema_agora.evaluation import EvaluationReport


@dataclass(frozen=True)
class ReadinessGate:
    name: str
    passed: bool
    rationale: str


@dataclass(frozen=True)
class ObservatorySnapshot:
    feedback_total: int
    accepted: int
    rejected: int
    corrected: int
    correction_rate: float
    evaluation_cases: int
    category_accuracy: float
    duplicate_f1: float
    summary_faithfulness_rate: float | None
    readiness: str
    gates: tuple[ReadinessGate, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["gates"] = [asdict(gate) for gate in self.gates]
        return data


def _feedback_counts(events: list[dict[str, Any]]) -> tuple[int, int, int, int]:
    values = [
        e.get("details", {}).get("feedback_type")
        for e in events
        if e.get("event_type") == "feedback_recorded"
    ]
    return (
        len(values),
        values.count("accepted"),
        values.count("rejected"),
        values.count("corrected"),
    )


def build_observatory_snapshot(
    report: EvaluationReport,
    feedback_events: list[dict[str, Any]],
    *,
    minimum_cases: int = 25,
    minimum_feedback: int = 20,
    minimum_category_accuracy: float = 0.80,
    minimum_duplicate_f1: float = 0.80,
    minimum_summary_faithfulness: float = 0.90,
) -> ObservatorySnapshot:
    total, accepted, rejected, corrected = _feedback_counts(feedback_events)
    correction_rate = corrected / total if total else 0.0

    gates = (
        ReadinessGate(
            "Evaluation sample size",
            report.cases_evaluated >= minimum_cases,
            f"{report.cases_evaluated}/{minimum_cases} labelled cases",
        ),
        ReadinessGate(
            "Reviewer feedback volume",
            total >= minimum_feedback,
            f"{total}/{minimum_feedback} feedback records",
        ),
        ReadinessGate(
            "Category accuracy",
            report.category_accuracy >= minimum_category_accuracy,
            f"{report.category_accuracy:.1%} >= {minimum_category_accuracy:.1%}",
        ),
        ReadinessGate(
            "Duplicate F1",
            report.duplicate_f1 >= minimum_duplicate_f1,
            f"{report.duplicate_f1:.1%} >= {minimum_duplicate_f1:.1%}",
        ),
        ReadinessGate(
            "Summary faithfulness",
            report.summary_faithfulness_rate is not None
            and report.summary_faithfulness_rate >= minimum_summary_faithfulness,
            (
                "Not measured"
                if report.summary_faithfulness_rate is None
                else f"{report.summary_faithfulness_rate:.1%} >= {minimum_summary_faithfulness:.1%}"
            ),
        ),
    )
    readiness = "READY_FOR_REVIEW" if all(gate.passed for gate in gates) else "NOT_READY"
    return ObservatorySnapshot(
        feedback_total=total,
        accepted=accepted,
        rejected=rejected,
        corrected=corrected,
        correction_rate=correction_rate,
        evaluation_cases=report.cases_evaluated,
        category_accuracy=report.category_accuracy,
        duplicate_f1=report.duplicate_f1,
        summary_faithfulness_rate=report.summary_faithfulness_rate,
        readiness=readiness,
        gates=gates,
    )
