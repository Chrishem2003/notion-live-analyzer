"""Evidence intake adapter contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from hashlib import sha256

from .models import EvidenceRecord, IntakeRequest


class EvidenceIntakeAdapter(ABC):
    """Base contract for converting source material into evidence records."""

    @abstractmethod
    def intake(self, request: IntakeRequest) -> EvidenceRecord | None:
        raise NotImplementedError


class TextEvidenceAdapter(EvidenceIntakeAdapter):
    """Accept textual source material and create deterministic evidence IDs."""

    def intake(self, request: IntakeRequest) -> EvidenceRecord | None:
        content = request.content.strip()

        if not content:
            return None

        title = request.title.strip() or request.source_id

        identity = "\n".join(
            (
                request.source_id,
                request.source,
                request.source_type,
                title,
                content,
                request.location or "",
            )
        )

        digest = sha256(identity.encode("utf-8")).hexdigest()
        evidence_id = f"{request.source_id}:{digest[:16]}"

        return EvidenceRecord.create(
            evidence_id=evidence_id,
            source_id=request.source_id,
            source=request.source,
            source_type=request.source_type,
            title=title,
            content=content,
            location=request.location,
            metadata=request.metadata,
        )
