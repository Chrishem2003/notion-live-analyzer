"""End-to-end governed case assembly for the NEMA-AGORA pilot."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
from .evidence_case import EvidenceCase, EvidenceReference, AdvisoryFinding, build_evidence_case, attach_human_review, mark_exported, validate_evidence_case

@dataclass(frozen=True)
class CasePipelineResult:
    case: EvidenceCase
    validation: dict[str, Any]

def assemble_case(*,case_id:str,observation:Mapping[str,Any],
                  evidence:list[EvidenceReference]|tuple[EvidenceReference,...],
                  findings:list[AdvisoryFinding]|tuple[AdvisoryFinding,...]=()) -> CasePipelineResult:
    """Assemble an evidence case without bypassing human review or export gates."""
    case=build_evidence_case(case_id=case_id,observation=observation,evidence=evidence,findings=findings)
    return CasePipelineResult(case,validate_evidence_case(case))

def review_case(result:CasePipelineResult,*,reviewer_id:str,role:str,decision:str,
                notes:str="") -> CasePipelineResult:
    case=attach_human_review(result.case,reviewer_id=reviewer_id,role=role,decision=decision,notes=notes)
    return CasePipelineResult(case,validate_evidence_case(case))

def export_case(result:CasePipelineResult) -> CasePipelineResult:
    case=mark_exported(result.case)
    return CasePipelineResult(case,validate_evidence_case(case))
