"""Reviewer workspace service for governed NEMA-AGORA evidence cases."""
from __future__ import annotations

from typing import Any
from .evidence_case import EvidenceCase, attach_human_review, mark_exported, validate_evidence_case
from .evidence_case_store import EvidenceCaseStore


class ReviewerWorkspace:
    def __init__(self, store: EvidenceCaseStore):
        self.store = store

    def inspect(self, case_id: str) -> dict[str, Any]:
        row = self.store.get(case_id)
        if row is None:
            raise KeyError(case_id)
        return {
            "case_id": case_id,
            "state": row["state"],
            "case_json": row["case_json"],
            "review_required": row["state"] == "READY_FOR_REVIEW",
            "execution_gate": "CLOSED",
            "events": self.store.list_events(case_id),
        }

    def review(
        self, case: EvidenceCase, *, reviewer_id: str, role: str,
        decision: str, notes: str = "", reviewed_at: str | None = None
    ) -> EvidenceCase:
        reviewed = attach_human_review(
            case, reviewer_id=reviewer_id, role=role,
            decision=decision, notes=notes, reviewed_at=reviewed_at,
        )
        self.store.append_event(
            case_id=reviewed.case_id, event_type="HUMAN_REVIEW",
            state=reviewed.state, actor_id=reviewer_id, role=role,
            event={"decision": decision, "notes": notes, "case_provenance_fingerprint": reviewed.provenance_fingerprint},
            created_at=reviewed.review.reviewed_at,
        )
        return reviewed

    def export_ready(
        self, case: EvidenceCase, *, actor_id: str = "system-reviewer",
        role: str = "reviewer"
    ) -> EvidenceCase:
        exported = mark_exported(case)
        self.store.append_event(
            case_id=exported.case_id, event_type="EXPORT_AUTHORISED",
            state=exported.state, actor_id=actor_id, role=role,
            event={"official_submission": False, "execution_gate": "CLOSED"},
            created_at=exported.review.reviewed_at,
        )
        return exported

    def validate(self, case: EvidenceCase) -> dict[str, Any]:
        return validate_evidence_case(case)
