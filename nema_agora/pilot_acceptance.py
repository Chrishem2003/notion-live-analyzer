"""End-to-end acceptance gates for the NEMA-AGORA pilot."""
from __future__ import annotations
from typing import Any
REQUIRED_BOUNDARIES=("human_review","non_submission","execution_closed","advisory_only")
def evaluate_pilot_acceptance(*,case_count:int,reviewed_count:int,exported_count:int,metrics:dict[str,Any]|None=None)->dict[str,Any]:
    issues=[]
    if case_count<0 or reviewed_count<0 or exported_count<0: issues.append("negative_counts")
    if reviewed_count>case_count: issues.append("reviewed_exceeds_cases")
    if exported_count>reviewed_count: issues.append("exported_exceeds_reviewed")
    if metrics:
        if metrics.get("execution_gate")!="CLOSED": issues.append("execution_gate_not_closed")
        if metrics.get("advisory_only") is not True: issues.append("advisory_boundary_missing")
        if metrics.get("regulatory_truth_claim") is not False: issues.append("truth_claim_boundary_missing")
    return {"schema":"nema-agora-pilot-acceptance-v1","valid":not issues,"issues":issues,
            "required_boundaries":REQUIRED_BOUNDARIES,"human_governed":True,
            "official_submission":False,"execution_gate":"CLOSED",
            "regulatory_conclusion":False,"emergency_dispatch":False}
