"""Operational metrics for governed NEMA-AGORA case workflows."""
from __future__ import annotations
from typing import Any
def summarize_case_metrics(cases:list[Any])->dict[str,Any]:
    total=len(cases); states={}
    for case in cases:
        state=getattr(case,"state","UNKNOWN"); states[state]=states.get(state,0)+1
    reviewed=sum(getattr(c,"review",None) is not None for c in cases)
    exported=sum(getattr(c,"state",None)=="EXPORTED" for c in cases)
    return {"schema":"nema-agora-ops-metrics-v1","case_count":total,"reviewed_count":reviewed,"exported_count":exported,"states":dict(sorted(states.items())),"human_review_coverage":reviewed/total if total else 0.0,"export_rate":exported/total if total else 0.0,"advisory_only":True,"regulatory_truth_claim":False,"execution_gate":"CLOSED"}
def validate_case_metrics(metrics:dict[str,Any])->dict[str,Any]:
    issues=[]
    for key in ("case_count","reviewed_count","exported_count"):
        if metrics.get(key,0)<0: issues.append(f"negative_{key}")
    if not 0<=metrics.get("human_review_coverage",-1)<=1: issues.append("invalid_review_coverage")
    if not 0<=metrics.get("export_rate",-1)<=1: issues.append("invalid_export_rate")
    return {"valid":not issues,"issues":issues,"schema":"nema-agora-ops-metrics-v1","advisory_only":True,"execution_gate":"CLOSED"}
