from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import ResearchEvidence


_SOURCE_RELIABILITY = {
    "repository": 0.90,
    "document": 0.85,
    "file": 0.85,
    "api": 0.80,
    "web": 0.70,
    "memory": 0.65,
    "unknown": 0.40,
}


def reliability_score(
    source_type: str,
    metadata: dict[str, Any] | None = None,
) -> float:

    score = _SOURCE_RELIABILITY.get(
        source_type.lower(),
        _SOURCE_RELIABILITY["unknown"],
    )

    metadata = metadata or {}

    if metadata.get("verified") is True:
        score += 0.10

    if metadata.get("trusted") is True:
        score += 0.10

    return min(1.0, score)


def freshness_score(
    evidence: ResearchEvidence,
) -> float:

    metadata = evidence.metadata

    timestamp = (
        metadata.get("updated_at")
        or metadata.get("published_at")
        or metadata.get("created_at")
    )

    if not timestamp:
        return 0.5

    try:
        value = str(timestamp).replace(
            "Z",
            "+00:00",
        )

        parsed = datetime.fromisoformat(value)

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        age_days = max(
            0.0,
            (
                datetime.now(timezone.utc)
                - parsed.astimezone(timezone.utc)
            ).total_seconds()
            / 86400.0,
        )

        if age_days <= 1:
            return 1.0

        if age_days <= 7:
            return 0.9

        if age_days <= 30:
            return 0.8

        if age_days <= 90:
            return 0.65

        if age_days <= 365:
            return 0.5

        return 0.3

    except (TypeError, ValueError):
        return 0.5


def completeness_score(
    evidence: ResearchEvidence,
) -> float:

    text = evidence.content.strip()

    if not text:
        return 0.0

    length = len(text)

    if length >= 1000:
        return 1.0

    if length >= 500:
        return 0.9

    if length >= 200:
        return 0.8

    if length >= 100:
        return 0.7

    if length >= 50:
        return 0.5

    return 0.3


def evaluate(
    evidence: ResearchEvidence,
) -> ResearchEvidence:

    evidence.reliability_score = reliability_score(
        evidence.source_type,
        evidence.metadata,
    )

    evidence.freshness_score = freshness_score(
        evidence
    )

    evidence.metadata[
        "completeness_score"
    ] = completeness_score(evidence)

    return evidence
