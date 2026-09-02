from __future__ import annotations

from typing import Any

from .models import EvidenceProvenance, ResearchEvidence


def infer_source_type(
    source: str,
    kind: str = "",
) -> str:

    normalized = (
        kind.strip().lower()
        or source.strip().lower()
    )

    if normalized in {
        "memory",
        "document",
        "file",
        "repository",
        "web",
        "api",
    }:
        return normalized

    if source.startswith(("http://", "https://")):
        return "web"

    return "unknown"


def build_provenance(
    source: str,
    source_type: str,
    metadata: dict[str, Any] | None = None,
) -> EvidenceProvenance:

    data = dict(metadata or {})

    identifier = str(
        data.get("id")
        or data.get("document_id")
        or data.get("chunk_id")
        or ""
    )

    location = str(
        data.get("location")
        or data.get("path")
        or source
    )

    return EvidenceProvenance.create(
        source=source,
        source_type=source_type,
        identifier=identifier,
        location=location,
        metadata=data,
    )


def provenance_score(
    evidence: ResearchEvidence,
) -> float:

    score = 0.0

    if evidence.source:
        score += 0.4

    if evidence.source_type != "unknown":
        score += 0.3

    if evidence.provenance is not None:
        score += 0.2

        if evidence.provenance.location:
            score += 0.1

    return min(1.0, score)
