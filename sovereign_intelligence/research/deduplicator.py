from __future__ import annotations

import re

from .models import ResearchEvidence


def _normalize(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        text.strip().lower(),
    )


def _fingerprint(text: str) -> str:
    normalized = _normalize(text)

    if len(normalized) <= 500:
        return normalized

    return normalized[:500]


def deduplicate(
    evidence: list[ResearchEvidence],
) -> tuple[list[ResearchEvidence], int]:

    unique: list[ResearchEvidence] = []
    seen: set[str] = set()

    for item in evidence:
        fingerprint = _fingerprint(item.content)

        if not fingerprint:
            continue

        if fingerprint in seen:
            continue

        seen.add(fingerprint)
        unique.append(item)

    return unique, len(evidence) - len(unique)
