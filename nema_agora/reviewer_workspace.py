"""Reviewer workspace service for NEMA-AGORA evidence cases.
Human decisions are explicit; this module never enforces or submits externally.
"""
from __future__ import annotations
from typing import Any
from .evidence_case import EvidenceCase, attach_human_review, mark_exported, validate_evidence_case
from .evidence_case_store import EvidenceCaseStore

class ReviewerWorkspace:
    def __init__(self, store: EvidenceCaseStore):
        self.store=store

    def inspect(self, case_id: str) -> dict[str, Any]:
        row=self.store.get(case_id)
        if row is None: raise KeyError(case_id)
        return {"case_id":case_id,"state":row["state"],"case_json":row["case_json"],
                "review_required":row["state"]=="READY_FOR_REVIEW","execution_gate":"CLOSED"}

    def review(self, case: EvidenceCase, *, reviewer_id:str, role:str,
               decision:str, notes:str="") -> EvidenceCase:
        reviewed=attach_human_review(case,reviewer_id=reviewer_id,role=role,
                                     decision=decision,notes=notes)
        return reviewed

    def export_ready(self, case: EvidenceCase) -> EvidenceCase:
        return mark_exported(case)

    def validate(self, case: EvidenceCase) -> dict[str,Any]:
        return validate_evidence_case(case)
