from __future__ import annotations

from typing import Any

from .retrieval_models import RetrievalResult


class EvidenceContextBuilder:

    def __init__(
        self,
        max_characters: int = 12000,
    ):

        self.max_characters = max_characters

    def build(
        self,
        result: RetrievalResult | None,
    ) -> str:

        if result is None:
            return ""

        if not result.candidates:
            return ""

        sections = []

        remaining = self.max_characters

        for index, candidate in enumerate(
            result.candidates,
            start=1,
        ):

            content = candidate.content.strip()

            if not content:
                continue

            section = (
                f"[Evidence {index}]\n"
                f"ID: {candidate.id}\n"
                f"Relevance: "
                f"{candidate.fused_score:.4f}\n"
                f"Lexical score: "
                f"{candidate.lexical_score:.4f}\n"
                f"Semantic score: "
                f"{candidate.semantic_score:.4f}\n"
                f"Content:\n"
                f"{content}\n"
            )

            if len(section) > remaining:
                section = section[:remaining]

            sections.append(section)

            remaining -= len(section)

            if remaining <= 0:
                break

        return "\n".join(sections)


def build_evidence_context(
    result: RetrievalResult | None,
    max_characters: int = 12000,
) -> str:

    return EvidenceContextBuilder(
        max_characters=max_characters
    ).build(result)
