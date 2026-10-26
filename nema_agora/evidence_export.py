"""Deterministic local export packaging for NEMA-AGORA cases."""
from __future__ import annotations
import json
from .evidence_case import EvidenceCase, validate_evidence_case

def build_export_package(case: EvidenceCase) -> dict:
    validation=validate_evidence_case(case)
    if not validation["valid"]: raise ValueError("cannot export invalid case")
    if case.state!="EXPORTED" or case.review is None: raise ValueError("case must be human-reviewed before export")
    return {"schema":"nema-agora-evidence-package-v1","case":case.to_dict(),
            "validation":validation,"official_submission":False,
            "environmental_truth_claim":False,"regulatory_conclusion":False,
            "execution_gate":"CLOSED"}

def export_json(case:EvidenceCase)->str:
    return json.dumps(build_export_package(case),sort_keys=True,indent=2,ensure_ascii=False)
