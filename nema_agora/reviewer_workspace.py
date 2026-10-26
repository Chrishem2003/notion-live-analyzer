"""Reviewer workspace service for governed NEMA-AGORA evidence cases."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .evidence_case import EvidenceCase, attach_human_review, mark_exported, validate_evidence_case
from .evidence_case_store import EvidenceCaseStore


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReviewerWorkspace:
    def __init__(self, store: EvidenceCaseStore):
        self.store = store

    def inspect(self, case_id: str) -> dict[str, Any]:
        case = self.store.load_case(case_id)
        return {
            "case_id": case.case_id,
            "state": case.state,
            "case_json": case.to_dict(),
            "review_required": case.state == "READY_FOR_REVIEW",
            "execution_gate": "CLOSED",
            "events": self.store.list_events(case_id),
        }

    def _assert_current(self, case: EvidenceCase) -> None:
        stored = self.store.load_case(case.case_id)
        if stored.provenance_fingerprint != case.provenance_fingerprint:
            raise ValueError("case provenance does not match persisted case")
        if stored.state != case.state:
            raise ValueError("case is stale relative to persisted transition history")

    def review(
        self, case: EvidenceCase, *, reviewer_id: str, role: str,
        decision: str, notes: str = "", reviewed_at: str | None = None
    ) -> EvidenceCase:
        self._assert_current(case)
        reviewed = attach_human_review(
            case, reviewer_id=reviewer_id, role=role,
            decision=decision, notes=notes, reviewed_at=reviewed_at,
        )
        self.store.append_event(
            case_id=reviewed.case_id,
            event_type="HUMAN_REVIEW",
            state=reviewed.state,
            actor_id=reviewer_id,
            role=role,
            event={
                "decision": decision,
                "notes": notes,
                "case_provenance_fingerprint": reviewed.provenance_fingerprint,
            },
            created_at=reviewed.review.reviewed_at,
        )
        return self.store.load_case(reviewed.case_id)

    def export_ready(
        self, case: EvidenceCase, *, actor_id: str = "system-reviewer",
        role: str = "reviewer", exported_at: str | None = None
    ) -> EvidenceCase:
        self._assert_current(case)
        exported = mark_exported(case)
        export_time = exported_at or _utc_now()
        self.store.append_event(
            case_id=exported.case_id,
            event_type="EXPORT_AUTHORISED",
            state=exported.state,
            actor_id=actor_id,
            role=role,
            event={
                "official_submission": False,
                "execution_gate": "CLOSED",
                "case_provenance_fingerprint": exported.provenance_fingerprint,
            },
            created_at=export_time,
        )
        return self.store.load_case(exported.case_id)

    def validate(self, case: EvidenceCase) -> dict[str, Any]:
        return validate_evidence_case(case)
