from __future__ import annotations

import math
import re
from collections import Counter


def tokenize(text: str) -> list[str]:

    return re.findall(
        r"[a-zA-Z0-9_]+",
        text.lower(),
    )


def term_frequency(text: str) -> Counter:

    return Counter(
        tokenize(text)
    )


def cosine_similarity(
    left: str,
    right: str,
) -> float:

    left_terms = term_frequency(left)
    right_terms = term_frequency(right)

    if not left_terms or not right_terms:
        return 0.0

    vocabulary = set(left_terms) | set(
        right_terms
    )

    dot = sum(
        left_terms[token]
        * right_terms[token]
        for token in vocabulary
    )

    left_norm = math.sqrt(
        sum(
            value * value
            for value in left_terms.values()
        )
    )

    right_norm = math.sqrt(
        sum(
            value * value
            for value in right_terms.values()
        )
    )

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return dot / (
        left_norm * right_norm
    )


def semantic_score(
    query: str,
    document: str,
) -> float:

    return cosine_similarity(
        query,
        document,
    )
