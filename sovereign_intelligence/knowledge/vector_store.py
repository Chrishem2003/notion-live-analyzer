from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VectorRecord:

    id: str

    content: str

    vector: list[float]

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class VectorMatch:

    id: str

    content: str

    score: float

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class VectorStore(ABC):

    @abstractmethod
    def upsert(
        self,
        record: VectorRecord,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        vector: list[float],
        top_k: int = 10,
    ) -> list[VectorMatch]:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError
