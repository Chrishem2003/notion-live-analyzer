"""Phase 29 — evidence synthesis and claim-boundary governance.

Turns prior phase outputs into an auditable evidence narrative. This module
never converts software/workflow evidence into environmental impact, regulatory,
NEMA, or production claims.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib, json
from typing import Any, Mapping

POLICY_VERSION = "phase29-v1"
DOMAINS = ("ENGINEERING","WORKFLOW_OUTCOMES","HUMAN_GOVERNANCE","REPRODUCIBILITY","ACCESSIBILITY","FIELD_EVALUATION")

@dataclass(frozen=True)
class EvidenceClaim:
    claim_id: str
    claim: str
    evidence_domain: str
    evidence_type: str
    source_ids: tuple[str, ...]
    sample_size: int
    limitations: tuple[str, ...]
    support_status: str = "SUPPORTED_WITH_LIMITATIONS"
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class EvidenceSynthesis:
    synthesis_id: str
    policy_version: str
    domains: dict[str, dict[str, Any]]
    claims: tuple[EvidenceClaim, ...]
    limitations: tuple[str, ...]
    evidence_fingerprint: str
    decision_notice: str = (
        "Evidence synthesis describes engineering, workflow, governance and "
        "research evidence only; it does not establish environmental impact, "
        "environmental truth, regulatory status, NEMA authorization, production "
        "approval, enforcement authority, or autonomous decision authority."
    )
    def to_dict(self): return asdict(self)

def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def build_evidence_synthesis(*, evidence_domains: Mapping[str, Mapping[str, Any]],
                             claims: list[EvidenceClaim] | None = None,
                             global_limitations: tuple[str, ...] = ()) -> EvidenceSynthesis:
    domains={}
    for name, raw in evidence_domains.items():
        key=str(name).upper()
        if key not in DOMAINS:
            raise ValueError(f"Unsupported evidence domain: {key}")
        source_ids=tuple(str(x) for x in raw.get("source_ids", ()) if str(x).strip())
        count=max(0,int(raw.get("count",0)))
        domains[key]={
            "count":count,
            "sample_size":max(0,int(raw.get("sample_size",count))),
            "source_ids":list(source_ids),
            "metrics":dict(raw.get("metrics",{})),
            "limitations":list(raw.get("limitations",())),
        }
    selected=tuple(claims or _default_claims(domains))
    for claim in selected:
        if claim.evidence_domain not in domains:
            raise ValueError(f"Claim references unavailable domain: {claim.evidence_domain}")
    payload={"domains":domains,"claims":[c.to_dict() for c in selected],"limitations":list(global_limitations)}
    digest=_fingerprint(payload)
    return EvidenceSynthesis(
        synthesis_id="SYN-"+digest[:16].upper(),policy_version=POLICY_VERSION,
        domains=domains,claims=selected,limitations=tuple(global_limitations),
        evidence_fingerprint=digest)

def _default_claims(domains: Mapping[str, Mapping[str, Any]]) -> list[EvidenceClaim]:
    specs=[
        ("CLM-01","The prototype has documented engineering controls and tested workflow components.","ENGINEERING","TEST_AND_CONTROL_EVIDENCE"),
        ("CLM-02","The controlled outcome layer can quantify baseline-versus-assisted workflow differences when paired observations exist.","WORKFLOW_OUTCOMES","PAIRED_OUTCOME_EVIDENCE"),
        ("CLM-03","Human review and lifecycle governance remain explicit control points in the evaluation architecture.","HUMAN_GOVERNANCE","GOVERNANCE_EVIDENCE"),
        ("CLM-04","Evaluation artifacts can be bound to reproducible software and dataset identities.","REPRODUCIBILITY","REPRODUCIBILITY_EVIDENCE"),
        ("CLM-05","The prototype explicitly measures participation and accessibility conditions without requiring identifying participant data.","ACCESSIBILITY","ACCESSIBILITY_EVIDENCE"),
        ("CLM-06","Controlled field scenarios exercise observation quality, advisory intelligence and reviewer-support behaviour.","FIELD_EVALUATION","SCENARIO_EVIDENCE"),
    ]
    out=[]
    for cid,claim,domain,etype in specs:
        d=domains.get(domain,{})
        count=int(d.get("count",0)); sources=tuple(d.get("source_ids",()))
        limits=tuple(d.get("limitations",())) or ("Evidence volume and representativeness must be assessed before generalisation.",)
        status="SUPPORTED_WITH_LIMITATIONS" if count>0 and sources else "EVIDENCE_THIN"
        out.append(EvidenceClaim(cid,claim,domain,etype,sources,int(d.get("sample_size",count)),limits,status))
    return out

def validate_synthesis(synthesis: EvidenceSynthesis) -> dict[str, Any]:
    errors=[]
    for claim in synthesis.claims:
        if claim.evidence_domain not in synthesis.domains: errors.append(f"CLAIM_DOMAIN_MISSING:{claim.claim_id}")
        if claim.sample_size < 0: errors.append(f"NEGATIVE_SAMPLE_SIZE:{claim.claim_id}")
        if not claim.limitations: errors.append(f"LIMITATION_MISSING:{claim.claim_id}")
    return {"valid":not errors,"errors":errors,"claims":len(synthesis.claims),"domains":len(synthesis.domains),
            "policy_version":POLICY_VERSION,"decision_notice":synthesis.decision_notice}

def serialise_synthesis(synthesis: EvidenceSynthesis) -> str:
    return json.dumps(synthesis.to_dict(),sort_keys=True,indent=2,ensure_ascii=False)
