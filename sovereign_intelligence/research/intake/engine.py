"""Evidence intake engine for Stage 47."""

from __future__ import annotations

from collections.abc import Iterable

from .adapters import EvidenceIntakeAdapter, TextEvidenceAdapter
from .models import EvidenceRecord, IntakeRequest, IntakeResult


class EvidenceIntakeEngine:
    """Coordinate source-material normalization into evidence records."""

    def __init__(
        self,
        adapters: Iterable[EvidenceIntakeAdapter] | None = None,
    ) -> None:
        self._adapters = list(adapters or [TextEvidenceAdapter()])

    @property
    def adapters(self) -> tuple[EvidenceIntakeAdapter, ...]:
        return tuple(self._adapters)

    def add_adapter(self, adapter: EvidenceIntakeAdapter) -> None:
        self._adapters.append(adapter)

    def intake(self, request: IntakeRequest) -> EvidenceRecord | None:
        for adapter in self._adapters:
            record = adapter.intake(request)

            if record is not None:
                return record

        return None

    def intake_many(
        self,
        requests: Iterable[IntakeRequest],
    ) -> IntakeResult:
        request_list = list(requests)

        accepted: list[EvidenceRecord] = []
        rejected: list[dict[str, str]] = []

        for request in request_list:
            record = self.intake(request)

            if record is None:
                rejected.append(
                    {
                        "source_id": request.source_id,
                        "reason": "no_adapter_accepted_source",
                    }
                )
                continue

            accepted.append(record)

        return IntakeResult(
            records=tuple(accepted),
            rejected=tuple(rejected),
            metadata={
                "adapter_count": len(self._adapters),
                "requested_count": len(request_list),
            },
        )
