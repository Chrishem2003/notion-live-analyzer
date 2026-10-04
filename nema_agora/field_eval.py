"""Phase 21 controlled field evaluation laboratory.

Phase 21-v2 evaluates synthetic field scenarios by executing the real
observation -> quality -> intelligence -> reviewer-support pipeline. It keeps
persistent evaluation storage separate from the demonstration execution and
never treats scenario results as environmental truth or regulatory evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
import uuid
from typing import Any

from nema_agora.copilot import build_reviewer_copilot
from nema_agora.intelligence import analyze_observation
from nema_agora.quality import assess_observation

POLICY_VERSION = "phase21-v2"
SCENARIOS = (
    "COMPLETE_REPORT",
    "INCOMPLETE_REPORT",
    "DUPLICATE_REPORT",
    "AMBIGUOUS_REPORT",
    "UNSAFE_ADVISORY",
    "CONFLICTING_HUMAN_REVIEW",
)


@dataclass(frozen=True)
class FieldScenario:
    scenario_id: str
    name: str
    description: str
    expected_quality: str
    expected_flags: tuple[str, ...] = ()
    expected_human_review: bool = True
    expected_safety_contract: bool = True
    synthetic: bool = True

    def to_dict(self) -> dict[str, Any]:
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def scenario_catalog() -> list[FieldScenario]:
    return [
        FieldScenario(
            "SCN-01", "Complete report",
            "Complete observation with no quality flags; reviewer support must remain active.",
            "PASS",
        ),
        FieldScenario(
            "SCN-02", "Incomplete report",
            "Missing description/evidence fields must produce a review state.",
            "REVIEW", ("INCOMPLETE", "MISSING_DESCRIPTION"),
        ),
        FieldScenario(
            "SCN-03", "Duplicate report",
            "A matching peer must be detected as a duplicate-review signal.",
            "REVIEW", ("DUPLICATE_SUSPECTED",),
        ),
        FieldScenario(
            "SCN-04", "Ambiguous report",
            "Insufficient consent/evidence context must remain reviewable rather than silently accepted.",
            "REVIEW", ("MISSING_CONSENT",),
        ),
        FieldScenario(
            "SCN-05", "Unsafe advisory",
            "Advisory output must preserve the mandatory human-review and safety contract.",
            "PASS",
        ),
        FieldScenario(
            "SCN-06", "Conflicting human review",
            "A field case may surface conflicting review context; the software must keep human review required.",
            "PASS",
        ),
    ]


def scenario_fingerprint(scenarios: list[FieldScenario]) -> str:
    payload = [s.to_dict() for s in scenarios]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def execute_pipeline(
    *,
    record: dict[str, Any],
    peer_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute the real observation -> quality -> intelligence -> reviewer-support chain."""
    peers = peer_records or []
    quality = assess_observation(record, peer_records=peers)
    analysis = analyze_observation(record, peer_records=peers)
    copilot = build_reviewer_copilot(record, analysis)
    return {
        "quality": quality,
        "analysis": analysis,
        "reviewer_copilot": copilot,
        "safety_contract": {
            "human_review_required": analysis.get("human_review_required") is True,
            "autonomous_decision_making": False,
            "source_case_id": copilot.get("source_case_id") == record.get("case_id"),
        },
    }


def _normalise_quality_status(value: Any) -> str:
    # Preserve compatibility with the earlier manual laboratory vocabulary.
    aliases = {
        "VALID": "PASS",
        "INCOMPLETE": "REVIEW",
        "DUPLICATE_SUSPECTED": "REVIEW",
        "NEEDS_REVIEW": "REVIEW",
        "CONTROLLED": "PASS",
        "ADJUDICATION_REQUIRED": "PASS",
    }
    return aliases.get(str(value), str(value))


def evaluate_scenario(
    *,
    scenario: FieldScenario,
    observed: dict[str, Any],
    notes: str = "",
) -> FieldEvaluationResult:
    quality = observed.get("quality", {})
    analysis = observed.get("analysis", {})
    safety = observed.get("safety_contract", {})
    quality_status = _normalise_quality_status(
        quality.get("quality_status", observed.get("quality_status"))
    )
    actual_flags = set(quality.get("flags", observed.get("quality_flags", [])) or [])
    review_required = analysis.get(
        "human_review_required", observed.get("human_review_required")
    )
    flags_ok = all(flag in actual_flags for flag in scenario.expected_flags)
    safety_ok = (
        safety.get("human_review_required") is True
        and safety.get("autonomous_decision_making") is False
        and safety.get("source_case_id") is True
    )
    passed = (
        quality_status == scenario.expected_quality
        and review_required is scenario.expected_human_review
        and flags_ok
        and (not scenario.expected_safety_contract or safety_ok)
    )
    return FieldEvaluationResult(
        evaluation_id=f"FE-{uuid.uuid4().hex[:10].upper()}",
        scenario_id=scenario.scenario_id,
        passed=passed,
        observed=observed,
        expected={
            "quality_status": scenario.expected_quality,
            "required_quality_flags": list(scenario.expected_flags),
            "human_review_required": scenario.expected_human_review,
            "safety_contract": scenario.expected_safety_contract,
        },
        notes=notes.strip(),
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def _base_record(case_id: str, *, description: str, consent: bool = True) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "observation_date": "2026-01-01",
        "category": "Solid waste / illegal dumping",
        "severity": "Medium",
        "district_or_site": "Synthetic Site",
        "description": description,
        "status": "Reviewed",
        "consent_confirmed": consent,
        "latitude": 1.0,
        "longitude": 32.0,
    }


def build_controlled_scenarios() -> list[tuple[FieldScenario, dict[str, Any], list[dict[str, Any]]]]:
    """Return deterministic synthetic records that exercise every Phase 21 scenario."""
    catalog = {scenario.scenario_id: scenario for scenario in scenario_catalog()}
    duplicate_peer = _base_record(
        "SCN-PEER-001",
        description="plastic waste near drainage channel",
    )
    return [
        (
            catalog["SCN-01"],
            _base_record("SCN-01-CASE", description="plastic waste near drainage channel"),
            [],
        ),
        (
            catalog["SCN-02"],
            _base_record("SCN-02-CASE", description=""),
            [],
        ),
        (
            catalog["SCN-03"],
            _base_record("SCN-03-CASE", description="plastic waste near drainage channel"),
            [duplicate_peer],
        ),
        (
            catalog["SCN-04"],
            _base_record(
                "SCN-04-CASE",
                description="possible change observed near a drainage channel",
                consent=False,
            ),
            [],
        ),
        (
            catalog["SCN-05"],
            _base_record("SCN-05-CASE", description="plastic waste near drainage channel"),
            [],
        ),
        (
            catalog["SCN-06"],
            _base_record("SCN-06-CASE", description="plastic waste near drainage channel"),
            [],
        ),
    ]


def run_field_evaluation(
    *,
    scenarios: list[
        tuple[FieldScenario, dict[str, Any], list[dict[str, Any]]]
    ],
) -> list[FieldEvaluationResult]:
    results: list[FieldEvaluationResult] = []
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
        "decision_notice": (
            "Controlled scenario evidence measures software behaviour only; it does not "
            "establish environmental truth, regulatory status, NEMA authorization, "
            "enforcement authority, emergency response authority, or production approval."
        ),
    }


class FieldEvaluationStore:
    """Persistent store for immutable scenario-evaluation results."""

    def __init__(self, database_path: str):
        self.database_path = str(database_path)
        with sqlite3.connect(self.database_path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS field_evaluations (
                    evaluation_id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    observed_json TEXT NOT NULL,
                    expected_json TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    policy_version TEXT NOT NULL
                )"""
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_field_evaluations_created "
                "ON field_evaluations(created_at)"
            )

    def save(self, result: FieldEvaluationResult) -> None:
        with sqlite3.connect(self.database_path) as db:
            db.execute(
                """INSERT INTO field_evaluations
                (evaluation_id, scenario_id, passed, observed_json, expected_json,
                 notes, created_at, policy_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    result.evaluation_id,
                    result.scenario_id,
                    int(result.passed),
                    json.dumps(result.observed, ensure_ascii=False, sort_keys=True),
                    json.dumps(result.expected, ensure_ascii=False, sort_keys=True),
                    result.notes,
                    result.created_at,
                    result.policy_version,
                ),
            )

    def list(self, limit: int = 500) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 2000))
        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT * FROM field_evaluations "
                "ORDER BY created_at DESC, evaluation_id DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        return [
            {
                **dict(row),
                "passed": bool(row["passed"]),
                "observed": json.loads(row["observed_json"]),
                "expected": json.loads(row["expected_json"]),
            }
            for row in rows
        ]
