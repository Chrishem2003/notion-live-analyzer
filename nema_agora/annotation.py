"""Phase 14 human annotation and dataset-governance primitives.

Annotations are human judgements, not environmental truth. The module supports
blind independent labels, disagreement measurement, and explicit adjudication.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import uuid
from typing import Any

from nema_agora.core import CATEGORIES


@dataclass(frozen=True)
class Annotation:
    annotation_id: str
    case_id: str
    annotator_id: str
    dataset_version: str
    category: str
    duplicate: bool
    summary_faithful: bool | None
    notes: str
    created_at: str

    def __post_init__(self) -> None:
        if not self.annotation_id.strip() or not self.case_id.strip() or not self.annotator_id.strip():
            raise ValueError("annotation_id, case_id and annotator_id are required")
        if self.category not in CATEGORIES:
            raise ValueError("Unsupported annotation category")
        if not self.dataset_version.strip():
            raise ValueError("dataset_version is required")
        if not isinstance(self.duplicate, bool):
            raise ValueError("duplicate must be boolean")
        if self.summary_faithful is not None and not isinstance(self.summary_faithful, bool):
            raise ValueError("summary_faithful must be boolean or null")
        if len(self.notes) > 1000:
            raise ValueError("Annotation notes must be 1,000 characters or fewer")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_annotation_id() -> str:
    return f"ANN-{uuid.uuid4().hex[:10].upper()}"


def make_annotation(
    *,
    case_id: str,
    annotator_id: str,
    dataset_version: str,
    category: str,
    duplicate: bool,
    summary_faithful: bool | None,
    notes: str = "",
    created_at: str | None = None,
) -> Annotation:
    return Annotation(
        annotation_id=new_annotation_id(),
        case_id=case_id.strip(),
        annotator_id=annotator_id.strip(),
        dataset_version=dataset_version.strip()[:80],
        category=category,
        duplicate=duplicate,
        summary_faithful=summary_faithful,
        notes=notes.strip(),
        created_at=created_at or datetime.now().astimezone().isoformat(timespec="seconds"),
    )


def _agreement(values_a: list[Any], values_b: list[Any]) -> float:
    if not values_a or len(values_a) != len(values_b):
        return 0.0
    return sum(a == b for a, b in zip(values_a, values_b)) / len(values_a)


def _cohen_kappa(values_a: list[Any], values_b: list[Any]) -> float:
    if not values_a or len(values_a) != len(values_b):
        return 0.0
    po = _agreement(values_a, values_b)
    categories = sorted(set(values_a) | set(values_b), key=str)
    pe = sum(
        (sum(a == category for a in values_a) / len(values_a))
        * (sum(b == category for b in values_b) / len(values_b))
        for category in categories
    )
    return 1.0 if pe == 1.0 else (po - pe) / (1.0 - pe)


def pairwise_agreement(first: list[Annotation], second: list[Annotation]) -> dict[str, Any]:
    """Compare two annotators only on case IDs they both independently labelled."""
    a = {x.case_id: x for x in first}
    b = {x.case_id: x for x in second}
    common = sorted(set(a) & set(b))
    if not common:
        return {
            "cases_compared": 0,
            "category_observed_agreement": 0.0,
            "category_cohen_kappa": 0.0,
            "duplicate_observed_agreement": 0.0,
        }
    cats_a = [a[k].category for k in common]
    cats_b = [b[k].category for k in common]
    dup_a = [a[k].duplicate for k in common]
    dup_b = [b[k].duplicate for k in common]
    return {
        "cases_compared": len(common),
        "category_observed_agreement": _agreement(cats_a, cats_b),
        "category_cohen_kappa": _cohen_kappa(cats_a, cats_b),
        "duplicate_observed_agreement": _agreement(dup_a, dup_b),
    }


class AnnotationStore:
    """SQLite-backed annotation store with blind-read helpers."""

    def __init__(self, database_path: str):
        import sqlite3
        self.database_path = str(database_path)
        with sqlite3.connect(self.database_path) as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS annotations (
                    annotation_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    annotator_id TEXT NOT NULL,
                    dataset_version TEXT NOT NULL,
                    category TEXT NOT NULL,
                    duplicate INTEGER NOT NULL CHECK (duplicate IN (0,1)),
                    summary_faithful INTEGER,
                    notes TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(case_id, annotator_id, dataset_version)
                )"""
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_annotations_case_version ON annotations(case_id, dataset_version)"
            )

    def save(self, annotation: Annotation) -> None:
        import sqlite3
        with sqlite3.connect(self.database_path) as db:
            db.execute(
                """INSERT INTO annotations
                (annotation_id, case_id, annotator_id, dataset_version, category,
                 duplicate, summary_faithful, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    annotation.annotation_id, annotation.case_id, annotation.annotator_id,
                    annotation.dataset_version, annotation.category,
                    int(annotation.duplicate),
                    None if annotation.summary_faithful is None else int(annotation.summary_faithful),
                    annotation.notes, annotation.created_at,
                ),
            )

    def list_for_annotator(self, annotator_id: str, dataset_version: str) -> list[Annotation]:
        return self._list("WHERE annotator_id = ? AND dataset_version = ?", (annotator_id, dataset_version))

    def list_for_case(self, case_id: str, dataset_version: str) -> list[Annotation]:
        return self._list("WHERE case_id = ? AND dataset_version = ?", (case_id, dataset_version))

    def list_all(self, dataset_version: str) -> list[Annotation]:
        return self._list("WHERE dataset_version = ?", (dataset_version,))

    def _list(self, where: str, args: tuple[Any, ...]) -> list[Annotation]:
        import sqlite3
        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT * FROM annotations " + where + " ORDER BY created_at, annotation_id", args
            ).fetchall()
        return [
            Annotation(
                annotation_id=r["annotation_id"], case_id=r["case_id"], annotator_id=r["annotator_id"],
                dataset_version=r["dataset_version"], category=r["category"],
                duplicate=bool(r["duplicate"]),
                summary_faithful=None if r["summary_faithful"] is None else bool(r["summary_faithful"]),
                notes=r["notes"], created_at=r["created_at"],
            )
            for r in rows
        ]

    def export_dataset(self, dataset_version: str) -> str:
        return json.dumps(
            [a.to_dict() for a in self.list_all(dataset_version)],
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
