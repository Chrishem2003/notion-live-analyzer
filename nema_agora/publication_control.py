"""Phase 32 — publication and evaluation control gate.

This gate checks report completeness, evidence lineage, source coverage, sample
size disclosure, limitations and explicit human sign-off. It never publishes
or authorizes a report automatically.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib, json
from typing import Any, Mapping

POLICY_VERSION="phase32-v1"
APPROVAL_STATES=("DRAFT","SUBMITTED_FOR_REVIEW","APPROVED_FOR_PUBLICATION","REJECTED")

@dataclass(frozen=True)
class PublicationPolicy:
    minimum_linked_claims:int=1
    require_valid_graph:bool=True
    require_all_claims_sourced:bool=True
    require_limitations:bool=True
    require_human_signoff:bool=True
    policy_version:str=POLICY_VERSION

@dataclass(frozen=True)
class PublicationDecision:
    decision_id:str
    report_id:str
    status:str
    gates:dict[str,bool]
    blockers:tuple[str,...]
    reviewer_id:str|None
    rationale:str
    evidence_fingerprint:str
    policy_version:str=POLICY_VERSION
    decision_notice:str=("Publication readiness is a documentation control only. It is not "
        "NEMA authorization, regulatory approval, environmental truth or impact, "
        "production approval, enforcement or emergency-response authority.")
    def to_dict(self): return asdict(self)

def _fp(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def evaluate_publication_gate(*, report:Mapping[str,Any], graph_validation:Mapping[str,Any],
                              policy:PublicationPolicy|None=None, reviewer_id:str|None=None,
                              rationale:str="")->PublicationDecision:
    policy=policy or PublicationPolicy()
    claims=list(report.get("claim_evidence_limitation_matrix",()))
    linked=[c for c in claims if any(str(x).strip() for x in c.get("source_ids",()))]
    all_sourced=bool(claims) and len(linked)==len(claims)
    all_limited=bool(claims) and all(bool(c.get("limitations")) for c in claims)
    report_id=str(report.get("report_id","")).strip()
    graph_ok=bool(graph_validation.get("valid",False))
    sample_sizes_valid=all(isinstance(c.get("sample_size",0),int) and c.get("sample_size",0)>=0 for c in claims)
    gates={
        "report_identity_present":bool(report_id),
        "minimum_linked_claims":len(linked)>=policy.minimum_linked_claims,
        "graph_valid":graph_ok if policy.require_valid_graph else True,
        "all_claims_sourced":all_sourced if policy.require_all_claims_sourced else True,
        "claim_limitations_present":all_limited if policy.require_limitations else True,
        "sample_sizes_disclosed":sample_sizes_valid,
        "human_signoff":bool(reviewer_id and reviewer_id.strip() and rationale and rationale.strip()) if policy.require_human_signoff else True,
    }
    blockers=tuple(k for k,v in gates.items() if not v)
    ready=not blockers
    status="APPROVED_FOR_PUBLICATION" if ready else "CONTROL_REQUIRED"
    evidence={"report_id":report_id,"claims":claims,"graph_validation":dict(graph_validation),
              "gates":gates,"reviewer_id":reviewer_id,"rationale":rationale,"policy":asdict(policy)}
    digest=_fp(evidence)
    return PublicationDecision("PUB-"+digest[:16].upper(),report_id,status,gates,blockers,
        reviewer_id.strip() if reviewer_id and reviewer_id.strip() else None,
        rationale.strip(),digest)

def validate_publication_decision(decision:PublicationDecision)->dict[str,Any]:
    errors=[]
    if decision.status not in ("APPROVED_FOR_PUBLICATION","CONTROL_REQUIRED"): errors.append("INVALID_STATUS")
    if decision.status=="APPROVED_FOR_PUBLICATION" and (decision.blockers or not all(decision.gates.values())):
        errors.append("APPROVED_WITH_FAILED_GATES")
    if decision.status=="APPROVED_FOR_PUBLICATION" and (not decision.reviewer_id or not decision.rationale.strip()):
        errors.append("APPROVAL_WITHOUT_HUMAN_SIGNOFF")
    if set(decision.blockers)!={k for k,v in decision.gates.items() if not v}: errors.append("BLOCKER_GATE_MISMATCH")
    return {"valid":not errors,"errors":errors,"status":decision.status,"blockers":list(decision.blockers),
            "policy_version":POLICY_VERSION,"decision_notice":decision.decision_notice}

def serialise_publication_decision(decision:PublicationDecision)->str:
    return json.dumps(decision.to_dict(),sort_keys=True,indent=2,ensure_ascii=False)
