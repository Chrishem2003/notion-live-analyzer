"""Explainable evidence-intelligence helpers for NEMA-AGORA.

This module is deliberately deterministic and local. It is an AI-ready
human-in-the-loop foundation, not an autonomous environmental decision-maker.
Outputs are advisory: they never establish truth, illegality, urgency,
regulatory priority, or enforcement action.
"""
from __future__ import annotations

import re
from typing import Any

from nema_agora.quality import assess_observation

_CATEGORY_TERMS = {
    "Solid waste / illegal dumping": {"waste", "dump", "dumping", "garbage", "litter", "rubbish", "plastic"},
    "Water pollution": {"water", "river", "stream", "drainage", "sewage", "effluent", "oil", "pollution"},
    "Wetland or land disturbance": {"wetland", "swamp", "land", "soil", "excavation", "clearing", "construction"},
    "Biodiversity / wildlife observation": {"wildlife", "bird", "animal", "fish", "forest", "tree", "species", "biodiversity"},
    "Air / noise pollution": {"smoke", "air", "dust", "noise", "emission", "burning"},
}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(text).casefold()))


def summarize_observation(record: dict[str, Any], max_chars: int = 240) -> str:
    """Create a neutral extractive summary without adding facts."""
    description = " ".join(str(record.get("description", "")).split())
    if not description:
        return "No observation description supplied."
    if len(description) <= max_chars:
        return description
    shortened = description[: max_chars - 1].rsplit(" ", 1)[0].strip()
    return shortened + "…"


def suggest_categories(record: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    """Rank keyword-supported category suggestions; existing category is not overwritten."""
    tokens = _tokens(record.get("description", ""))
    ranked = []
    for category, terms in _CATEGORY_TERMS.items():
        matches = sorted(tokens & terms)
        if matches:
            ranked.append({"category": category, "matched_terms": matches, "score": len(matches)})
    ranked.sort(key=lambda item: (-item["score"], item["category"]))
    return ranked[:limit]


def priority_advisory(record: dict[str, Any], quality: dict[str, Any]) -> dict[str, str]:
    """Return a non-regulatory review-priority hint."""
    severity = str(record.get("severity", "")).strip()
    if quality["quality_status"] != "PASS":
        return {"level": "REVIEW", "reason": "Resolve data-quality flags before relying on this record."}
    if severity == "High":
        return {"level": "HIGH_REVIEW", "reason": "The submitter selected High; a human reviewer should verify the record."}
    if severity == "Urgent":
        return {"level": "BLOCKED_BY_SCOPE", "reason": "Urgent incident handling is outside the pilot governance scope."}
    return {"level": "NORMAL_REVIEW", "reason": "No additional deterministic review signal was generated."}


def duplicate_candidates(record: dict[str, Any], peer_records: list[dict[str, Any]] | None = None) -> list[str]:
    """Return case IDs of records that match the quality module's duplicate heuristic."""
    peers = peer_records or []
    matches = []
    target_tokens = _tokens(record.get("description", ""))
    for peer in peers:
        if peer.get("case_id") == record.get("case_id"):
            continue
        if (
            str(peer.get("district_or_site", "")).strip().casefold()
            != str(record.get("district_or_site", "")).strip().casefold()
            or peer.get("category") != record.get("category")
            or peer.get("observation_date") != record.get("observation_date")
        ):
            continue
        peer_tokens = _tokens(peer.get("description", ""))
        if target_tokens and peer_tokens:
            overlap = len(target_tokens & peer_tokens) / max(1, min(len(target_tokens), len(peer_tokens)))
            if overlap >= 0.8:
                matches.append(str(peer.get("case_id")))
    return matches


def analyze_observation(
    record: dict[str, Any], *, peer_records: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Produce an explainable advisory analysis for human review."""
    peers = peer_records or []
    quality = assess_observation(record, peer_records=peers)
    candidates = duplicate_candidates(record, peers)
    suggestions = suggest_categories(record)
    advisory = priority_advisory(record, quality)
    return {
        "summary": summarize_observation(record),
        "category_suggestions": suggestions,
        "priority_advisory": advisory,
        "quality_status": quality["quality_status"],
        "quality_flags": quality["flags"],
        "duplicate_candidates": candidates,
        "human_review_required": True,
        "decision_notice": (
            "Advisory only. This analysis does not establish environmental truth, "
            "illegality, urgency, regulatory priority, or enforcement action."
        ),
    }
