"""Deterministic, human-governed evidence case/provenance bundle for NEMA-AGORA."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib, json
from typing import Any, Mapping

POLICY_VERSION = "evidence-case-v1"
ALLOWED_STATES = {"DRAFT","READY_FOR_REVIEW","REVIEWED","EXPORTED"}
ALLOWED_DECISIONS = {"PENDING","ACKNOWLEDGED","REQUIRES_FOLLOW_UP","ESCALATED"}

def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",",":"), ensure_ascii=False)

def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()

def _utc(value: str | None = None) -> str:
    return value or datetime.now(timezone.utc).isoformat()

@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    kind: str
    source: str
    captured_at: str
    content_fingerprint: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class AdvisoryFinding:
    finding_id: str
    model_id: str
    model_version: str
    summary: str
    confidence: float | None
    input_fingerprints: tuple[str,...]
    generated_at: str
    advisory_only: bool = True

@dataclass(frozen=True)
class HumanReview:
    reviewer_id: str
    role: str
    decision: str
    reviewed_at: str
    notes: str = ""

@dataclass(frozen=True)
class EvidenceCase:
    case_id: str
    created_at: str
    state: str
    observation_fingerprint: str
    evidence: tuple[EvidenceReference,...]
    findings: tuple[AdvisoryFinding,...] = ()
    review: HumanReview | None = None
    provenance_fingerprint: str = ""
    def to_dict(self) -> dict[str,Any]:
        return asdict(self)

def build_evidence_case(*,case_id:str,observation:Mapping[str,Any],
                        evidence:list[EvidenceReference]|tuple[EvidenceReference,...],
                        findings:list[AdvisoryFinding]|tuple[AdvisoryFinding,...]=(),
                        created_at:str|None=None) -> EvidenceCase:
    if not case_id.strip(): raise ValueError("case_id is required")
    refs=tuple(evidence)
    if len({r.evidence_id for r in refs}) != len(refs): raise ValueError("evidence_id values must be unique")
    for f in findings:
        if not f.advisory_only: raise ValueError("findings must remain advisory_only")
        if f.confidence is not None and not 0 <= f.confidence <= 1: raise ValueError("confidence must be between 0 and 1")
    created=_utc(created_at); obs_fp=_fingerprint(observation)
    provenance=_fingerprint({"policy_version":POLICY_VERSION,"case_id":case_id,
        "observation_fingerprint":obs_fp,"evidence":[asdict(r) for r in refs],
        "findings":[asdict(f) for f in findings]})
    return EvidenceCase(case_id,created,"READY_FOR_REVIEW",obs_fp,refs,tuple(findings),None,provenance)

def attach_human_review(case:EvidenceCase,*,reviewer_id:str,role:str,decision:str,
                        reviewed_at:str|None=None,notes:str="") -> EvidenceCase:
    if case.state not in {"READY_FOR_REVIEW","REVIEWED"}: raise ValueError("case is not reviewable in its current state")
    if not reviewer_id.strip() or not role.strip(): raise ValueError("reviewer_id and role are required")
    if decision not in ALLOWED_DECISIONS-{"PENDING"}: raise ValueError("invalid human review decision")
    review=HumanReview(reviewer_id,role,decision,_utc(reviewed_at),notes)
    return EvidenceCase(case.case_id,case.created_at,"REVIEWED",case.observation_fingerprint,
                        case.evidence,case.findings,review,case.provenance_fingerprint)

def mark_exported(case:EvidenceCase) -> EvidenceCase:
    if case.state != "REVIEWED" or case.review is None: raise ValueError("only human-reviewed cases can be exported")
    return EvidenceCase(case.case_id,case.created_at,"EXPORTED",case.observation_fingerprint,
                        case.evidence,case.findings,case.review,case.provenance_fingerprint)

def validate_evidence_case(case:EvidenceCase) -> dict[str,Any]:
    issues=[]
    if case.state not in ALLOWED_STATES: issues.append("invalid_state")
    if not case.case_id or not case.observation_fingerprint: issues.append("missing_identity")
    if len({r.evidence_id for r in case.evidence}) != len(case.evidence): issues.append("duplicate_evidence_id")
    for f in case.findings:
        if not f.advisory_only: issues.append("non_advisory_finding")
        if f.confidence is not None and not 0 <= f.confidence <= 1: issues.append("invalid_confidence")
    if case.state in {"REVIEWED","EXPORTED"} and case.review is None: issues.append("review_missing")
    return {"policy_version":POLICY_VERSION,"case_id":case.case_id,"state":case.state,
            "valid":not issues,"issues":issues,"human_governed":True,
            "automatic_repair":False,"execution_gate":"CLOSED",
            "environmental_truth_claim":False,"regulatory_conclusion":False,
            "nema_authorization":False,"emergency_dispatch":False}
