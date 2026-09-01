from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .vector_store import (
    VectorMatch,
    VectorRecord,
    VectorStore,
)


class JsonVectorStore(VectorStore):

    def __init__(
        self,
        path: str = "data/sovereign_embedding_store.json",
    ):

        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._records: dict[
            str,
            VectorRecord,
        ] = {}

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

        except (
            OSError,
            ValueError,
            TypeError,
        ):

            return

        if not isinstance(payload, list):
            return

        for item in payload:

            try:

                record = VectorRecord(
                    id=str(item["id"]),
                    content=str(
                        item["content"]
                    ),
                    vector=[
                        float(value)
                        for value in item[
                            "vector"
                        ]
                    ],
                    metadata=dict(
                        item.get(
                            "metadata",
                            {},
                        )
                    ),
                )

                self._records[
                    record.id
                ] = record

            except (
                KeyError,
                TypeError,
                ValueError,
            ):

                continue

    def _save(self):

        payload = []

        for record in self._records.values():

            payload.append(
                {
                    "id": record.id,
                    "content": record.content,
                    "vector": record.vector,
                    "metadata": record.metadata,
                }
            )

        temporary = self.path.with_suffix(
            ".tmp"
        )

        temporary.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        temporary.replace(self.path)

    def upsert(
        self,
        record: VectorRecord,
    ):

        if not record.id:
            raise ValueError(
                "Vector record ID is required."
            )

        if not record.vector:
            raise ValueError(
                "Vector cannot be empty."
            )

        self._records[
            record.id
        ] = record

        self._save()

    def search(
        self,
        vector: list[float],
        top_k: int = 10,
    ) -> list[VectorMatch]:

        if not vector:
            return []

        matches = []

        for record in self._records.values():

            if len(record.vector) != len(
                vector
            ):
                continue

            dot = sum(
                left * right
                for left, right in zip(
                    vector,
                    record.vector,
                )
            )

            left_norm = math.sqrt(
                sum(
                    value * value
                    for value in vector
                )
            )

            right_norm = math.sqrt(
                sum(
                    value * value
                    for value in record.vector
                )
            )

            if (
                left_norm == 0
                or right_norm == 0
            ):
                score = 0.0

            else:

                score = dot / (
                    left_norm
                    * right_norm
                )

            matches.append(
                VectorMatch(
                    id=record.id,
                    content=record.content,
                    score=score,
                    metadata=record.metadata,
                )
            )

        matches.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        return matches[:top_k]

    def count(self) -> int:

        return len(self._records)

    def clear(self):

        self._records.clear()

        self._save()
