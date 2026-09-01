from __future__ import annotations

from typing import Any

from .lexical_retriever import (
    lexical_similarity,
)
from .hybrid_fusion import (
    HybridFusion,
)
from .reranker import (
    DiversityReranker,
)
from .retrieval_models import (
    RetrievalCandidate,
    RetrievalResult,
)


class HybridRetriever:

    def __init__(
        self,
        semantic_index=None,
        lexical_weight: float = 0.35,
        semantic_weight: float = 0.65,
    ):

        self.semantic_index = (
            semantic_index
        )

        self.documents: dict[
            str,
            RetrievalCandidate,
        ] = {}

        self.fusion = HybridFusion(
            lexical_weight=lexical_weight,
            semantic_weight=semantic_weight,
        )

        self.reranker = (
            DiversityReranker()
        )

    def add(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any]
        | None = None,
    ):

        self.documents[
            document_id
        ] = RetrievalCandidate(
            id=document_id,
            content=content,
            metadata=metadata or {},
        )

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> RetrievalResult:

        lexical = []

        for candidate in self.documents.values():

            score = lexical_similarity(
                query,
                candidate.content,
            )

            lexical.append(
                RetrievalCandidate(
                    id=candidate.id,
                    content=candidate.content,
                    lexical_score=score,
                    metadata=candidate.metadata,
                )
            )

        lexical.sort(
            key=lambda item: item.lexical_score,
            reverse=True,
        )

        lexical = lexical[
            :max(top_k * 3, top_k)
        ]

        semantic = []

        if self.semantic_index:

            try:

                semantic_matches = (
                    self.semantic_index.search(
                        query,
                        top_k=max(
                            top_k * 3,
                            top_k,
                        ),
                    )
                )

                for match in semantic_matches:

                    semantic.append(
                        RetrievalCandidate(
                            id=match.id,
                            content=match.content,
                            semantic_score=match.score,
                            metadata=match.metadata,
                        )
                    )

            except Exception:

                semantic = []

        result = self.fusion.combine(
            query=query,
            lexical=lexical,
            semantic=semantic,
            top_k=max(
                top_k * 3,
                top_k,
            ),
        )

        result.candidates = (
            self.reranker.rerank(
                result.candidates,
                top_k=top_k,
            )
        )

        return result
