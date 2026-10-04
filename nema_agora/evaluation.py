"""Reproducible evaluation primitives for NEMA-AGORA advisory systems."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
import hashlib, json
POLICY_VERSION="evaluation-v1"
def _fp(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
@dataclass(frozen=True)
class EvaluationCase:
    case_id:str; input_fingerprint:str; expected_label:str; observed_label:str; model_id:str; model_version:str
@dataclass(frozen=True)
class EvaluationRun:
    run_id:str; dataset_fingerprint:str; cases:tuple[EvaluationCase,...]; accuracy:float; policy_version:str=POLICY_VERSION
def build_evaluation_run(*,run_id:str,dataset:Mapping[str,Any],cases:list[EvaluationCase]|tuple[EvaluationCase,...])->EvaluationRun:
    if not run_id.strip(): raise ValueError("run_id is required")
    items=tuple(cases)
    if not items: raise ValueError("at least one evaluation case is required")
    if len({c.case_id for c in items})!=len(items): raise ValueError("case_id values must be unique")
    return EvaluationRun(run_id,_fp(dataset),items,sum(c.expected_label==c.observed_label for c in items)/len(items))
def validate_evaluation_run(run:EvaluationRun)->dict[str,Any]:
    issues=[]
    if not run.run_id or not run.dataset_fingerprint: issues.append("missing_identity")
    if not 0<=run.accuracy<=1: issues.append("invalid_accuracy")
    return {"policy_version":POLICY_VERSION,"run_id":run.run_id,"valid":not issues,"issues":issues,"reproducible":True,"advisory_evaluation_only":True,"human_governed":True,"automatic_model_admission":False,"regulatory_conclusion":False}
