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


@dataclass(frozen=True)
class Adjudication:
    adjudication_id: str
    case_id: str
    adjudicator_id: str
    dataset_version: str
    final_category: str
    final_duplicate: bool
    final_summary_faithful: bool | None
    rationale: str
    created_at: str

    def __post_init__(self) -> None:
        if self.final_category not in CATEGORIES:
            raise ValueError("Unsupported adjudicated category")
        if not self.adjudicator_id.strip() or not self.case_id.strip():
            raise ValueError("case_id and adjudicator_id are required")
        if not self.rationale.strip() or len(self.rationale) > 1500:
            raise ValueError("Adjudication rationale is required and must be <=1,500 characters")


def make_adjudication(
    *,
    case_id: str,
    adjudicator_id: str,
    dataset_version: str,
    final_category: str,
    final_duplicate: bool,
    final_summary_faithful: bool | None,
    rationale: str,
    created_at: str | None = None,
) -> Adjudication:
    return Adjudication(
        adjudication_id=f"ADJ-{uuid.uuid4().hex[:10].upper()}",
        case_id=case_id.strip(),
        adjudicator_id=adjudicator_id.strip(),
        dataset_version=dataset_version.strip()[:80],
        final_category=final_category,
        final_duplicate=final_duplicate,
        final_summary_faithful=final_summary_faithful,
        rationale=rationale.strip(),
        created_at=created_at or datetime.now().astimezone().isoformat(timespec="seconds"),
    )


def disagreement_cases(annotations: list[Annotation]) -> list[str]:
    grouped: dict[str, list[Annotation]] = {}
    for item in annotations:
        grouped.setdefault(item.case_id, []).append(item)
    return sorted(
        case_id for case_id, rows in grouped.items()
        if len(rows) >= 2 and (
            len({r.category for r in rows}) > 1
            or len({r.duplicate for r in rows}) > 1
            or len({r.summary_faithful for r in rows if r.summary_faithful is not None}) > 1
        )
    )


# Extend the store with explicit adjudication records. Adjudication never
# overwrites the underlying independent annotations.
def _save_adjudication(self: AnnotationStore, item: Adjudication) -> None:
    import sqlite3
    with sqlite3.connect(self.database_path) as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS annotation_adjudications (
                adjudication_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                adjudicator_id TEXT NOT NULL,
                dataset_version TEXT NOT NULL,
                final_category TEXT NOT NULL,
                final_duplicate INTEGER NOT NULL CHECK (final_duplicate IN (0,1)),
                final_summary_faithful INTEGER,
                rationale TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        db.execute(
            """INSERT INTO annotation_adjudications
            (adjudication_id, case_id, adjudicator_id, dataset_version,
             final_category, final_duplicate, final_summary_faithful, rationale, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.adjudication_id, item.case_id, item.adjudicator_id,
                item.dataset_version, item.final_category, int(item.final_duplicate),
                None if item.final_summary_faithful is None else int(item.final_summary_faithful),
                item.rationale, item.created_at,
            ),
        )


def _list_adjudications(self: AnnotationStore, dataset_version: str) -> list[Adjudication]:
    import sqlite3
    with sqlite3.connect(self.database_path) as db:
        db.row_factory = sqlite3.Row
        db.execute(
            """CREATE TABLE IF NOT EXISTS annotation_adjudications (
                adjudication_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                adjudicator_id TEXT NOT NULL,
                dataset_version TEXT NOT NULL,
                final_category TEXT NOT NULL,
                final_duplicate INTEGER NOT NULL,
                final_summary_faithful INTEGER,
                rationale TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        rows = db.execute(
            "SELECT * FROM annotation_adjudications WHERE dataset_version = ? ORDER BY created_at, adjudication_id",
            (dataset_version,),
        ).fetchall()
    return [
        Adjudication(
            adjudication_id=r["adjudication_id"], case_id=r["case_id"],
            adjudicator_id=r["adjudicator_id"], dataset_version=r["dataset_version"],
            final_category=r["final_category"], final_duplicate=bool(r["final_duplicate"]),
            final_summary_faithful=None if r["final_summary_faithful"] is None else bool(r["final_summary_faithful"]),
            rationale=r["rationale"], created_at=r["created_at"],
        ) for r in rows
    ]


AnnotationStore.save_adjudication = _save_adjudication
AnnotationStore.list_adjudications = _list_adjudications
