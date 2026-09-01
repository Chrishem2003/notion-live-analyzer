from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any


def _tokenize(text: str) -> list[str]:

    return re.findall(
        r"[a-zA-Z0-9_]+",
        text.lower(),
    )


def _vector(text: str) -> dict[str, float]:

    tokens = _tokenize(text)

    if not tokens:
        return {}

    counts: dict[str, float] = {}

    for token in tokens:
        counts[token] = (
            counts.get(token, 0.0) + 1.0
        )

    magnitude = math.sqrt(
        sum(
            value * value
            for value in counts.values()
        )
    )

    if magnitude == 0:
        return {}

    return {
        token: value / magnitude
        for token, value in counts.items()
    }


def _similarity(
    left: dict[str, float],
    right: dict[str, float],
) -> float:

    if not left or not right:
        return 0.0

    if len(left) > len(right):
        left, right = right, left

    return sum(
        value * right.get(token, 0.0)
        for token, value in left.items()
    )


class PersistentVectorIndex:

    def __init__(
        self,
        path: str = "data/sovereign_vectors.json",
    ):

        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.documents: list[dict[str, Any]] = []

        self._load()

    def _load(self):

        if not self.path.exists():
            return

        try:

            payload = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )

            if isinstance(payload, list):
                self.documents = payload

        except (
            OSError,
            ValueError,
            TypeError,
        ):

            self.documents = []

    def _save(self):

        temporary = self.path.with_suffix(
            ".tmp"
        )

        temporary.write_text(
            json.dumps(
                self.documents,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        temporary.replace(self.path)

    def add(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        document_id: str | None = None,
    ):

        if not content.strip():
            raise ValueError(
                "Cannot index empty content."
            )

        record = {
            "id": document_id,
            "content": content,
            "metadata": metadata or {},
            "vector": _vector(content),
        }

        self.documents.append(record)

        self._save()

        return record["id"]

    def add_many(
        self,
        documents: list[dict[str, Any]],
    ):

        for document in documents:

            content = str(
                document.get(
                    "content",
                    "",
                )
            )

            if not content.strip():
                continue

            self.documents.append(
                {
                    "id": document.get("id"),
                    "content": content,
                    "metadata": document.get(
                        "metadata",
                        {},
                    ),
                    "vector": _vector(content),
                }
            )

        self._save()

    def search(
        self,
        query: str,
        top_k: int = 10,
    ):

        query_vector = _vector(query)

        results = []

        for record in self.documents:

            score = _similarity(
                query_vector,
                record.get(
                    "vector",
                    {},
                ),
            )

            results.append(
                {
                    "id": record.get("id"),
                    "content": record.get(
                        "content",
                        "",
                    ),
                    "metadata": record.get(
                        "metadata",
                        {},
                    ),
                    "score": score,
                }
            )

        results.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return results[:top_k]

    def count(self) -> int:

        return len(self.documents)

    def clear(self):

        self.documents = []

        self._save()
