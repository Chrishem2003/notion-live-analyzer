from __future__ import annotations

from typing import Any

from .embedding_service import EmbeddingService
from .vector_store import (
    VectorMatch,
    VectorRecord,
    VectorStore,
)


class SemanticIndex:

    def __init__(
        self,
        embeddings: EmbeddingService | None = None,
        store: VectorStore | None = None,
    ):

        from .json_vector_store import (
            JsonVectorStore,
        )

        self.embeddings = (
            embeddings
            or EmbeddingService()
        )

        self.store = (
            store
            or JsonVectorStore()
        )

    def add(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any]
        | None = None,
    ):

        vector = self.embeddings.embed_one(
            content
        )

        self.store.upsert(
            VectorRecord(
                id=document_id,
                content=content,
                vector=vector,
                metadata=metadata or {},
            )
        )

    def add_many(
        self,
        documents: list[dict[str, Any]],
    ):

        valid = [
            document
            for document in documents
            if str(
                document.get(
                    "content",
                    "",
                )
            ).strip()
        ]

        if not valid:
            return

        texts = [
            str(
                document["content"]
            )
            for document in valid
        ]

        result = self.embeddings.embed(
            texts
        )

        for document, vector in zip(
            valid,
            result.vectors,
        ):

            self.store.upsert(
                VectorRecord(
                    id=str(
                        document["id"]
                    ),
                    content=str(
                        document["content"]
                    ),
                    vector=vector,
                    metadata=document.get(
                        "metadata",
                        {},
                    ),
                )
            )

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[VectorMatch]:

        vector = self.embeddings.embed_one(
            query
        )

        return self.store.search(
            vector,
            top_k=top_k,
        )

    def count(self) -> int:

        return self.store.count()
