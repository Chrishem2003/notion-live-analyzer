from __future__ import annotations

from pathlib import Path

from .retrieval_engine import HybridRetriever
from .evidence_context import build_evidence_context


class KnowledgeEngine:

    def __init__(self):

        self.retriever = HybridRetriever()

    def add_document(
        self,
        document_id: str,
        content: str,
        metadata: dict | None = None,
    ):

        self.retriever.add(
            document_id=document_id,
            content=content,
            metadata=metadata or {},
        )

    def add_file(
        self,
        path: str,
        document_id: str | None = None,
    ):

        file = Path(path)

        if not file.exists():
            raise FileNotFoundError(
                str(file)
            )

        content = file.read_text(
            encoding="utf-8",
            errors="replace",
        )

        self.add_document(
            document_id=(
                document_id
                or str(file)
            ),
            content=content,
            metadata={
                "source": str(file),
                "filename": file.name,
                "extension": file.suffix,
            },
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
    ):

        return self.retriever.search(
            query=query,
            top_k=top_k,
        )

    def context(
        self,
        query: str,
        top_k: int = 5,
        max_characters: int = 12000,
    ):

        result = self.search(
            query=query,
            top_k=top_k,
        )

        return (
            result,
            build_evidence_context(
                result,
                max_characters=max_characters,
            ),
        )
