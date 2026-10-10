"""Phase 31 — human-reviewed research and award dossier.

Creates a structured dossier from the Phase 29 synthesis and Phase 30 lineage
graph. It separates verified evidence from interpretation and limitations.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib, json
from typing import Any, Mapping

POLICY_VERSION="phase31-v1"

@dataclass(frozen=True)
class DossierSection:
    section_id:str
    title:str
    purpose:str
    content:str
    evidence_refs:tuple[str,...]
    limitations:tuple[str,...]
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class ResearchDossier:
    dossier_id:str
    title:str
    sections:tuple[DossierSection,...]
    claim_count:int
    linked_claim_count:int
    evidence_fingerprint:str
    review_status:str
    policy_version:str=POLICY_VERSION
    decision_notice:str=("Human-reviewed research/award documentation only. It does not "
        "establish environmental truth, environmental impact, regulatory status, "
        "NEMA authorization, production approval, enforcement, emergency response, "
        "or autonomous decision authority.")
    def to_dict(self): return asdict(self)

def _fp(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def build_dossier(*, synthesis:Mapping[str,Any], graph:Mapping[str,Any])->ResearchDossier:
    claims=list(synthesis.get("claims",()))
    linked=[c for c in claims if any(str(s).strip() for s in c.get("source_ids",()))]
    limitations=tuple(str(x) for x in synthesis.get("limitations",()) if str(x).strip())
    sections=(
        DossierSection("SEC-01","Executive Summary","Concise statement of what the evidence demonstrates.",
            "NEMA-AGORA is evaluated here as a governed environmental technology prototype with bounded engineering, workflow and research evidence.",
            tuple(str(c.get("claim_id")) for c in linked), limitations or ("Evidence is bounded by recorded evaluation artifacts.",)),
        DossierSection("SEC-02","Technical Contribution","Explain the system innovation without overstating outcomes.",
            "The architecture combines observation quality controls, advisory intelligence, human review, controlled evaluation, provenance and reproducibility into one governed workflow.",
            tuple(str(c.get("claim_id")) for c in linked), ("Technical capability is not evidence of environmental impact.",)),
        DossierSection("SEC-03","Evidence & Results","Present measured evidence and sample sizes.",
            "Measured results must be read from the linked evidence artifacts; this dossier does not invent missing measurements.",
            tuple(str(c.get("claim_id")) for c in linked), ("Sample size, selection and representativeness constrain generalisation.",)),
        DossierSection("SEC-04","Governance & Safety","Make human control and boundaries explicit.",
            "Model outputs remain advisory; workflow-changing decisions require human governance and controlled evidence.",
            tuple(str(c.get("claim_id")) for c in linked), ("No autonomous enforcement, emergency response or regulatory decision is authorized.",)),
        DossierSection("SEC-05","Limitations & Next Steps","Prevent overclaiming and define the next evidence needed.",
            "Further real-user or field evaluation requires appropriate permission, consent, safeguards and a documented evaluation protocol.",
            (), limitations or ("Further evidence is required before generalisation.",)),
    )
    payload={"claims":claims,"sections":[s.to_dict() for s in sections],"graph_fingerprint":graph.get("fingerprint")}
    digest=_fp(payload)
    status="READY_FOR_HUMAN_REVIEW" if linked and not graph.get("orphan_claims") and not graph.get("missing_parents") else "CONTROL_REQUIRED"
    return ResearchDossier("DOSSIER-"+digest[:16].upper(),"NEMA-AGORA Research & Award Dossier",sections,
        len(claims),len(linked),digest,status)

def validate_dossier(dossier:ResearchDossier)->dict[str,Any]:
    errors=[]
    if not dossier.sections: errors.append("NO_SECTIONS")
    if dossier.linked_claim_count>dossier.claim_count: errors.append("INVALID_LINKED_CLAIM_COUNT")
    if dossier.review_status not in ("READY_FOR_HUMAN_REVIEW","CONTROL_REQUIRED"): errors.append("INVALID_REVIEW_STATUS")
    for s in dossier.sections:
        if not s.content.strip(): errors.append("EMPTY_SECTION:"+s.section_id)
        if not s.limitations: errors.append("LIMITATION_MISSING:"+s.section_id)
    return {"valid":not errors,"errors":errors,"review_status":dossier.review_status,
            "policy_version":POLICY_VERSION,"decision_notice":dossier.decision_notice}

def serialise_dossier(dossier:ResearchDossier)->str:
    return json.dumps(dossier.to_dict(),sort_keys=True,indent=2,ensure_ascii=False)
