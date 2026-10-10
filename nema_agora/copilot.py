"""Reviewer copilot contracts for NEMA-AGORA.

Builds a structured, advisory reviewer view from existing deterministic
analysis. It never invents evidence, changes workflow state, or makes
regulatory/enforcement decisions.
"""
from __future__ import annotations

from typing import Any

COPILOT_VERSION = "phase10-v1"

_FORBIDDEN_KEYS = frozenset({
    "enforcement_action",
    "regulatory_decision",
    "official_incident_status",
    "automatic_workflow_transition",
    "emergency_dispatch",
})


def _evidence_facts(record: dict[str, Any]) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []
    labels = (
        ("Category supplied", "category"),
        ("Severity supplied", "severity"),
        ("Site label supplied", "district_or_site"),
        ("Observation date", "observation_date"),
        ("Description", "description"),
    )
    for label, key in labels:
        value = str(record.get(key, "")).strip()
        if value:
            if key == "description":
                value = " ".join(value.split())
                if len(value) > 240:
                    value = value[:239].rsplit(" ", 1)[0] + "…"
            facts.append({"label": label, "value": value, "source_field": key})
    for label, key in (("Latitude", "latitude"), ("Longitude", "longitude")):
        value = record.get(key)
        if isinstance(value, (int, float)):
            facts.append({"label": label, "value": str(value), "source_field": key})
    return facts


def _questions(analysis: dict[str, Any]) -> list[str]:
    questions: list[str] = []
    flags = set(analysis.get("quality_flags", []))
    if flags:
        questions.append("Can the reviewer resolve the listed data-quality signals before relying on this record?")
    if analysis.get("category_suggestions"):
        questions.append("Does the supplied category remain the best description after reviewing the matched terms?")
    if analysis.get("duplicate_candidates"):
        questions.append("Are the candidate records genuinely the same observation, or separate observations at the same site/date?")
    if not questions:
        questions.append("Is the record sufficiently supported by the information actually supplied?")
    return questions


def build_reviewer_copilot(
    record: dict[str, Any], analysis: dict[str, Any]
) -> dict[str, Any]:
    """Return a bounded reviewer checklist; all recommendations remain advisory."""
    source_case_id = str(record.get("case_id", "")).strip()
    if not source_case_id:
        raise ValueError("A source case ID is required.")
    result = {
        "copilot_version": COPILOT_VERSION,
        "source_case_id": source_case_id,
        "evidence_facts": _evidence_facts(record),
        "quality": {
            "status": analysis.get("quality_status", "UNKNOWN"),
            "flags": list(analysis.get("quality_flags", [])),
        },
        "category_review": {
            "supplied_category": str(record.get("category", "")).strip(),
            "suggestions": list(analysis.get("category_suggestions", [])),
        },
        "duplicate_review": {
            "candidate_case_ids": list(analysis.get("duplicate_candidates", [])),
            "human_confirmation_required": True,
        },
        "uncertainty_questions": _questions(analysis),
        "review_checklist": [
            "Confirm the observation matches the information actually supplied.",
            "Resolve material data-quality flags.",
            "Review category suggestions and accept or reject them with human judgement.",
            "Inspect duplicate candidates before treating records as distinct.",
            "Make any workflow/status change manually through the review controls.",
        ],
        "human_review_required": True,
        "decision_notice": (
            "Advisory reviewer support only. No environmental truth, illegality, "
            "regulatory decision, enforcement action, emergency dispatch, or "
            "automatic workflow transition is produced."
        ),
    }
    forbidden = _FORBIDDEN_KEYS.intersection(result)
    if forbidden:
        raise ValueError(f"Forbidden autonomous decision fields: {sorted(forbidden)}")
    return result
