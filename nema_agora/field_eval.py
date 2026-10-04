"""Phase 21 controlled field evaluation.

Runs real observation records through the existing quality and intelligence
pipeline before evaluating expected scenario behaviour. This closes the gap
between manually supplied observed values and actual system execution.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
import hashlib, json, uuid

from nema_agora.copilot import build_reviewer_copilot
from nema_agora.intelligence import analyze_observation
from nema_agora.quality import assess_observation

POLICY_VERSION = "phase21-v2"
SCENARIOS = ("COMPLETE_REPORT", "INCOMPLETE_REPORT", "DUPLICATE_REPORT",
             "AMBIGUOUS_REPORT", "UNSAFE_ADVISORY", "CONFLICTING_HUMAN_REVIEW")


@dataclass(frozen=True)
class FieldScenario:
    scenario_id: str
    name: str
    description: str
    expected_quality: str
    expected_human_review: bool = True
    synthetic: bool = True

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class FieldEvaluationResult:
    evaluation_id: str
    scenario_id: str
    passed: bool
    observed: dict[str, Any]
    expected: dict[str, Any]
    notes: str
    created_at: str
    policy_version: str = POLICY_VERSION

    def to_dict(self):
        return asdict(self)


def scenario_catalog() -> list[FieldScenario]:
    return [
        FieldScenario("SCN-01", "Complete report", "Complete observation requiring normal human review.", "PASS"),
        FieldScenario("SCN-02", "Incomplete report", "Missing required evidence or description.", "REVIEW"),
        FieldScenario("SCN-03", "Duplicate report", "Two reports with matching duplicate signals.", "REVIEW"),
        FieldScenario("SCN-04", "Ambiguous report", "Insufficient context requiring reviewer clarification.", "REVIEW"),
        FieldScenario("SCN-05", "Unsafe advisory", "Advisory output must retain the human-review contract.", "PASS"),
        FieldScenario("SCN-06", "Conflicting human review", "Reviewer disagreement remains subject to adjudication.", "PASS"),
    ]


def scenario_fingerprint(scenarios: list[FieldScenario]) -> str:
    payload = [s.to_dict() for s in scenarios]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def execute_pipeline(*, record: dict[str, Any], peer_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Execute the real observation → quality → intelligence → reviewer-support chain."""
    peers = peer_records or []
    quality = assess_observation(record, peer_records=peers)
    analysis = analyze_observation(record, peer_records=peers)
    copilot = build_reviewer_copilot(record, analysis)
    return {
        "quality": quality,
        "analysis": analysis,
        "reviewer_copilot": copilot,
    }


def evaluate_scenario(*, scenario: FieldScenario, observed: dict[str, Any], notes: str = "") -> FieldEvaluationResult:
    quality_status = observed.get("quality", {}).get("quality_status", observed.get("quality_status"))
    review_required = observed.get("analysis", {}).get(
        "human_review_required", observed.get("human_review_required")
    )
    passed = quality_status == scenario.expected_quality and review_required is scenario.expected_human_review
    return FieldEvaluationResult(
        evaluation_id=f"FE-{uuid.uuid4().hex[:10].upper()}",
        scenario_id=scenario.scenario_id,
        passed=passed,
        observed=observed,
        expected={"quality_status": scenario.expected_quality,
                  "human_review_required": scenario.expected_human_review},
        notes=notes.strip(),
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def run_field_evaluation(*, scenarios: list[tuple[FieldScenario, dict[str, Any], list[dict[str, Any]]]]) -> list[FieldEvaluationResult]:
    results = []
    for scenario, record, peers in scenarios:
        observed = execute_pipeline(record=record, peer_records=peers)
        results.append(evaluate_scenario(scenario=scenario, observed=observed))
    return results


def summarise_results(results: list[FieldEvaluationResult]) -> dict[str, Any]:
    total = len(results)
    passed = sum(r.passed for r in results)
    return {
        "policy_version": POLICY_VERSION,
        "total_scenarios": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": passed / total if total else 0.0,
        "scenario_ids": [r.scenario_id for r in results],
        "status": "PASS" if total and passed == total else ("PARTIAL" if passed else "NOT_READY"),
        "human_governance_required": True,
        "decision_notice": "Controlled scenario evidence measures software behaviour only; it does not establish environmental truth, regulatory status, NEMA authorization, enforcement authority, emergency response authority, or production approval.",
    }
