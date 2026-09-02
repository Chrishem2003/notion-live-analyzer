from __future__ import annotations

import re

from .models import ResearchQuery


_RESEARCH_PATTERNS = (
    r"\baccording to\b",
    r"\bevidence\b",
    r"\bsources?\b",
    r"\bresearch\b",
    r"\bverify\b",
    r"\bcompare\b",
    r"\bversus\b",
    r"\bvs\.?\b",
    r"\blatest\b",
    r"\bcurrent\b",
    r"\bupdated?\b",
    r"\bwhy\b",
    r"\bhow\b",
    r"\bwhat\b",
)


def detect_intent(query: str) -> str:
    text = query.strip().lower()

    if not text:
        return "general"

    if any(
        re.search(pattern, text)
        for pattern in (
            r"\bcompare\b",
            r"\bversus\b",
            r"\bvs\.?\b",
        )
    ):
        return "comparative"

    if any(
        re.search(pattern, text)
        for pattern in (
            r"\blatest\b",
            r"\bcurrent\b",
            r"\bupdated?\b",
            r"\btoday\b",
            r"\brecent\b",
        )
    ):
        return "freshness"

    if any(
        re.search(pattern, text)
        for pattern in (
            r"\bevidence\b",
            r"\bsources?\b",
            r"\bverify\b",
            r"\bresearch\b",
            r"\baccording to\b",
        )
    ):
        return "evidence"

    if any(
        re.search(pattern, text)
        for pattern in _RESEARCH_PATTERNS
    ):
        return "research"

    return "general"


def plan_query(
    query: str,
    max_results: int = 10,
) -> ResearchQuery:

    intent = detect_intent(query)

    return ResearchQuery(
        query=query.strip(),
        intent=intent,
        freshness_required=intent == "freshness",
        diversity_required=intent == "comparative",
        max_results=max(1, int(max_results)),
    )
