"""Evidence intake models for Stage 47 research discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class EvidenceRecord:
    """Normalized evidence captured from a discovered source."""

    evidence_id: str
    source_id: str
    source: str
    source_type: str
    title: str
    content: str
    location: str | None = None
    captured_at: datetime = field(default_factory=_utc_now)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        evidence_id: str,
        source_id: str,
        source: str,
        source_type: str,
        title: str,
        content: str,
        location: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "EvidenceRecord":
        return cls(
            evidence_id=evidence_id,
            source_id=source_id,
            source=source,
            source_type=source_type,
            title=title,
            content=content,
            location=location,
            metadata=dict(metadata or {}),
        )


@dataclass(frozen=True)
class IntakeRequest:
    """Request to convert source material into normalized evidence."""

    source_id: str
    source: str
    source_type: str
    title: str
    content: str
    location: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "IntakeRequest":
        return cls(
            source_id=str(value.get("source_id", "")),
            source=str(value.get("source", "")),
            source_type=str(value.get("source_type", "")),
            title=str(value.get("title", "")),
            content=str(value.get("content", "")),
            location=value.get("location"),
            metadata=dict(value.get("metadata") or {}),
        )


@dataclass(frozen=True)
class IntakeResult:
    """Result of an evidence intake operation."""

    records: Sequence[EvidenceRecord]
    rejected: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def accepted_count(self) -> int:
        return len(self.records)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)
