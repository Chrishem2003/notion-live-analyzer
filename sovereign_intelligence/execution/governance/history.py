from __future__ import annotations

from collections.abc import Iterable

from .models import DecisionRecord


class DecisionHistory:
    """
    In-memory ordered history of governance decisions.

    The history layer is deliberately independent from the existing
    memory subsystem so Stage 49 can be introduced without changing
    existing memory contracts.
    """

    def __init__(
        self,
        records: Iterable[DecisionRecord] | None = None,
    ) -> None:
        self._records: list[DecisionRecord] = list(records or [])

    def append(self, record: DecisionRecord) -> None:
        if not isinstance(record, DecisionRecord):
            raise TypeError("record must be a DecisionRecord")

        self._records.append(record)

    def all(self) -> tuple[DecisionRecord, ...]:
        return tuple(self._records)

    def latest(self) -> DecisionRecord | None:
        if not self._records:
            return None

        return self._records[-1]

    def count(self) -> int:
        return len(self._records)

    def actions(self) -> tuple[str, ...]:
        return tuple(record.action.value for record in self._records)

    def recent(
        self,
        limit: int = 5,
    ) -> tuple[DecisionRecord, ...]:
        if limit < 0:
            raise ValueError("limit must be >= 0")

        if limit == 0:
            return ()

        return tuple(self._records[-limit:])
