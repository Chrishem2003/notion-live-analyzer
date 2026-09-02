from __future__ import annotations

import re

from .models import DiscoveryPlan, ResearchObjective


_COMPARISON = re.compile(
    r"\b(compare|versus|vs\.?|difference|differences)\b",
    re.IGNORECASE,
)

_FRESHNESS = re.compile(
    r"\b(latest|recent|today|current|newest|up[- ]to[- ]date)\b",
    re.IGNORECASE,
)

_RESEARCH = re.compile(
    r"\b(research|investigate|analy[sz]e|evidence|sources?|study)\b",
    re.IGNORECASE,
)


def detect_intent(query: str) -> str:
    text = (query or "").strip()

    if _COMPARISON.search(text):
        return "comparative"

    if _FRESHNESS.search(text):
        return "freshness"

    if _RESEARCH.search(text):
        return "research"

    return "general"


def build_search_queries(query: str, intent: str) -> list[str]:
    text = " ".join((query or "").split())

    if not text:
        return []

    queries = [text]

    if intent == "comparative":
        queries.append(f"{text} comparison")

    elif intent == "freshness":
        queries.append(f"{text} latest")

    elif intent == "research":
        queries.append(f"{text} evidence")

    return list(dict.fromkeys(queries))


def plan_discovery(
    query: str,
    max_sources: int = 10,
) -> DiscoveryPlan:

    normalized = " ".join((query or "").split())
    intent = detect_intent(normalized)

    search_queries = build_search_queries(
        normalized,
        intent,
    )

    objective = ResearchObjective(
        objective_id="primary",
        description=(
            normalized
            if normalized
            else "No research objective supplied."
        ),
        priority=1.0,
        queries=tuple(search_queries),
    )

    source_types = [
        "document",
        "repository",
        "memory",
    ]

    if intent == "freshness":
        source_types.append("web")

    return DiscoveryPlan(
        query=normalized,
        intent=intent,
        objectives=[objective],
        source_types=source_types,
        search_queries=search_queries,
        freshness_required=intent == "freshness",
        diversity_required=intent in {
            "comparative",
            "research",
        },
        max_sources=max(1, int(max_sources)),
    )
