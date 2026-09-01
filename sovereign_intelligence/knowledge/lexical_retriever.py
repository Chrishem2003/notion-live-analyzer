from __future__ import annotations

import re

from .retrieval_models import (
    RetrievalCandidate,
)


def tokenize(text: str) -> set[str]:

    return set(
        re.findall(
            r"[a-zA-Z0-9_]+",
            text.lower(),
        )
    )


def lexical_similarity(
    query: str,
    document: str,
) -> float:

    query_tokens = tokenize(query)

    document_tokens = tokenize(document)

    if not query_tokens or not document_tokens:
        return 0.0

    overlap = (
        query_tokens
        & document_tokens
    )

    return len(overlap) / len(
        query_tokens
    )


class LexicalRetriever:

    def __init__(
        self,
        documents: list[
            RetrievalCandidate
        ] | None = None,
    ):

        self.documents = documents or []

    def add(
        self,
        candidate: RetrievalCandidate,
    ):

        self.documents.append(candidate)

    def search(
        self,
        query: str,
        top_k: int = 10,
    ):

        results = []

        for document in self.documents:

            score = lexical_similarity(
                query,
                document.content,
            )

            results.append(
                RetrievalCandidate(
                    id=document.id,
                    content=document.content,
                    lexical_score=score,
                    semantic_score=document.semantic_score,
                    fused_score=document.fused_score,
                    metadata=document.metadata,
                )
            )

        results.sort(
            key=lambda item: item.lexical_score,
            reverse=True,
        )

        return results[:top_k]
