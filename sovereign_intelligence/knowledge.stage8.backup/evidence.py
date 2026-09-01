from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .documents import read_text_document, chunk_text
from .retrieval import retrieve


@dataclass
class EvidenceItem:

    source: str
    content: str
    score: float = 0.0
    kind: str = "document"
    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class EvidenceManager:

    def __init__(
        self,
        memory=None,
        max_documents: int = 20,
        max_chunks_per_document: int = 20,
    ):

        self.memory = memory
        self.max_documents = max_documents
        self.max_chunks_per_document = (
            max_chunks_per_document
        )

    def memory_evidence(
        self,
        query: str,
        limit: int = 10,
    ) -> list[EvidenceItem]:

        if self.memory is None:
            return []

        memories = self.memory.store.recent(
            limit=limit
        )

        results = []

        documents = [
            memory["content"]
            for memory in memories
        ]

        if not documents:
            return []

        ranked = retrieve(
            query,
            documents,
            top_k=limit,
        )

        for score, content in ranked:

            matching = next(
                (
                    item
                    for item in memories
                    if item["content"] == content
                ),
                None,
            )

            metadata = (
                matching.get("metadata", {})
                if matching
                else {}
            )

            results.append(
                EvidenceItem(
                    source="memory",
                    content=content,
                    score=float(score),
                    kind="memory",
                    metadata=metadata,
                )
            )

        return results

    def document_evidence(
        self,
        query: str,
        paths: list[str],
        top_k: int = 10,
    ) -> list[EvidenceItem]:

        candidates = []

        for raw_path in paths[
            :self.max_documents
        ]:

            path = Path(raw_path)

            if not path.is_file():
                continue

            try:
                text = read_text_document(
                    str(path)
                )
            except Exception:
                continue

            chunks = chunk_text(text)[
                :self.max_chunks_per_document
            ]

            for index, chunk in enumerate(
                chunks
            ):

                candidates.append(
                    (
                        str(path),
                        index,
                        chunk,
                    )
                )

        if not candidates:
            return []

        documents = [
            item[2]
            for item in candidates
        ]

        ranked = retrieve(
            query,
            documents,
            top_k=top_k,
        )

        results = []

        for score, content in ranked:

            match = next(
                (
                    item
                    for item in candidates
                    if item[2] == content
                ),
                None,
            )

            if match is None:
                continue

            path, index, _ = match

            results.append(
                EvidenceItem(
                    source=path,
                    content=content,
                    score=float(score),
                    kind="document",
                    metadata={
                        "chunk_index": index,
                    },
                )
            )

        return results

    def collect(
        self,
        query: str,
        document_paths: list[str] | None = None,
        memory_limit: int = 10,
        document_limit: int = 10,
    ) -> list[EvidenceItem]:

        evidence = []

        evidence.extend(
            self.memory_evidence(
                query,
                limit=memory_limit,
            )
        )

        evidence.extend(
            self.document_evidence(
                query,
                document_paths or [],
                top_k=document_limit,
            )
        )

        evidence.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        return evidence

    def format_context(
        self,
        evidence: list[EvidenceItem],
        max_characters: int = 12000,
    ) -> str:

        if not evidence:
            return ""

        sections = []
        total = 0

        for index, item in enumerate(
            evidence,
            start=1,
        ):

            section = (
                f"[Evidence {index}]\n"
                f"Source: {item.source}\n"
                f"Type: {item.kind}\n"
                f"Relevance: {item.score:.4f}\n"
                f"Content:\n{item.content}\n"
            )

            if (
                total + len(section)
                > max_characters
            ):
                break

            sections.append(section)
            total += len(section)

        return "\n".join(sections)
