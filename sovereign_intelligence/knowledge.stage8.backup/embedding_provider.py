from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass
class EmbeddingResult:

    vectors: list[list[float]]

    model: str

    provider: str

    usage: dict[str, Any] = field(
        default_factory=dict
    )


class EmbeddingProvider(ABC):

    name = "embedding_provider"

    @abstractmethod
    def embed(
        self,
        texts: Sequence[str],
        model: str | None = None,
    ) -> EmbeddingResult:
        raise NotImplementedError


class EmbeddingError(RuntimeError):

    pass
