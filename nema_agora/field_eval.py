"""Phase 21 controlled field-evaluation laboratory.

Scenario-based evaluation of the complete NEMA-AGORA workflow using synthetic
or explicitly consented cases. Results are evidence about system behaviour, not
environmental truth, regulatory status, or NEMA authorization.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib, json, uuid
from typing import Any

POLICY_VERSION="phase21-v1"
SCENARIOS=("COMPLETE_REPORT","INCOMPLETE_REPORT","DUPLICATE_REPORT","AMBIGUOUS_REPORT","UNSAFE_ADVISORY","CONFLICTING_HUMAN_REVIEW")

@dataclass(frozen=True)
class FieldScenario:
    scenario_id:str
    name:str
    description:str
    expected_quality:str
    expected_human_review:bool=True
    synthetic:bool=True
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class FieldEvaluationResult:
    evaluation_id:str
    scenario_id:str
    passed:bool
    observed:dict[str,Any]
    expected:dict[str,Any]
    notes:str
    created_at:str
    policy_version:str=POLICY_VERSION
    def to_dict(self): return asdict(self)

def scenario_catalog()->list[FieldScenario]:
    return [
        FieldScenario("SCN-01","Complete report","Valid observation with complete description, consent and coordinates.","VALID"),
        FieldScenario("SCN-02","Incomplete report","Missing required evidence or description.","INCOMPLETE"),
        FieldScenario("SCN-03","Duplicate report","Two reports describing the same event.","DUPLICATE_SUSPECTED"),
        FieldScenario("SCN-04","Ambiguous report","Insufficient context requiring reviewer clarification.","NEEDS_REVIEW"),
        FieldScenario("SCN-05","Unsafe advisory","Model output violates the human-review safety contract.","CONTROLLED"),
        FieldScenario("SCN-06","Conflicting human review","Reviewers disagree and require adjudication.","ADJUDICATION_REQUIRED"),
    ]

def scenario_fingerprint(scenarios:list[FieldScenario])->str:
    payload=[s.to_dict() for s in scenarios]
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def evaluate_scenario(*,scenario:FieldScenario,observed:dict[str,Any],notes:str="")->FieldEvaluationResult:
    quality=observed.get("quality_status")
    review=bool(observed.get("human_review_required",scenario.expected_human_review))
    passed=(quality==scenario.expected_quality and review==scenario.expected_human_review)
    return FieldEvaluationResult(
        evaluation_id=f"FE-{uuid.uuid4().hex[:10].upper()}",
        scenario_id=scenario.scenario_id,passed=passed,observed=observed,
        expected={"quality_status":scenario.expected_quality,"human_review_required":scenario.expected_human_review},
        notes=notes.strip(),created_at=datetime.now().astimezone().isoformat(timespec="seconds"))

def summarise_results(results:list[FieldEvaluationResult])->dict[str,Any]:
    total=len(results); passed=sum(r.passed for r in results)
    return {"policy_version":POLICY_VERSION,"total_scenarios":total,"passed":passed,
            "failed":total-passed,"pass_rate":passed/total if total else 0.0,
            "scenario_ids":[r.scenario_id for r in results],
            "status":"PASS" if total and passed==total else ("PARTIAL" if passed else "NOT_READY"),
            "human_governance_required":True,
            "decision_notice":"Controlled scenario evidence does not establish environmental truth, regulatory status, NEMA authorization, enforcement authority, emergency response authority, or production approval."}
