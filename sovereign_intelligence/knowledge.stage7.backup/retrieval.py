from __future__ import annotations

import math
import re


def tokenize(text: str) -> set[str]:

    return set(
        re.findall(
            r"[a-zA-Z0-9_]+",
            text.lower(),
        )
    )


def lexical_score(
    query: str,
    document: str,
) -> float:

    q = tokenize(query)
    d = tokenize(document)

    if not q or not d:
        return 0.0

    intersection = len(q & d)

    return intersection / math.sqrt(
        len(q) * len(d)
    )


def retrieve(
    query: str,
    documents: list[str],
    top_k: int = 5,
):

    scored = [
        (
            lexical_score(query, document),
            document,
        )
        for document in documents
    ]

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return scored[:top_k]