"""Deterministic human-review report generation for NEMA-AGORA."""
from __future__ import annotations
import json
from .evidence_case import EvidenceCase,validate_evidence_case

def build_case_report(case:EvidenceCase)->dict:
    validation=validate_evidence_case(case)
    review=None if case.review is None else {"reviewer_id":case.review.reviewer_id,"role":case.review.role,"decision":case.review.decision,"reviewed_at":case.review.reviewed_at,"notes":case.review.notes}
    return {"schema":"nema-agora-case-report-v1","case_id":case.case_id,"state":case.state,"observation_fingerprint":case.observation_fingerprint,"evidence_count":len(case.evidence),"finding_count":len(case.findings),"review":review,"validation":validation,"official_submission":False,"execution_gate":"CLOSED"}

def report_json(case:EvidenceCase)->str:
    return json.dumps(build_case_report(case),sort_keys=True,indent=2,ensure_ascii=False)
