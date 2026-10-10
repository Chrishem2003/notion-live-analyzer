"""Phase 24 — Evidence Observatory.

Aggregates persisted evidence into a transparent scorecard. Scores describe
evidence coverage and system behaviour; they are never environmental truth,
regulatory status, NEMA authorization, or production approval.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
import json, hashlib, uuid

POLICY_VERSION="phase24-v1"
DOMAINS=("IMPACT","ACCESSIBILITY","PROVENANCE","FIELD_EVALUATION","HUMAN_GOVERNANCE")

@dataclass(frozen=True)
class EvidenceScorecard:
    scorecard_id:str
    generated_at:str
    domain_scores:dict
    evidence_counts:dict
    overall_coverage:float
    warnings:tuple[str,...]
    policy_version:str=POLICY_VERSION
    decision_notice:str="Evidence coverage is an engineering/research indicator only; it does not establish environmental impact, environmental truth, regulatory status, NEMA authorization, or production approval."
    def to_dict(self): return asdict(self)

def _coverage(count):
    return min(1.0,float(count)/10.0)

def build_scorecard(*,impact_count:int,accessibility_count:int,provenance_count:int,
                    field_evaluation_count:int,human_review_count:int)->EvidenceScorecard:
    counts={"IMPACT":max(0,impact_count),"ACCESSIBILITY":max(0,accessibility_count),
            "PROVENANCE":max(0,provenance_count),"FIELD_EVALUATION":max(0,field_evaluation_count),
            "HUMAN_GOVERNANCE":max(0,human_review_count)}
    scores={k:_coverage(v) for k,v in counts.items()}
    warnings=tuple(f"{k}_EVIDENCE_THIN" for k,v in counts.items() if v<10)
    return EvidenceScorecard(f"EV-{uuid.uuid4().hex[:10].upper()}",
        datetime.now().astimezone().isoformat(timespec="seconds"),scores,counts,
        sum(scores.values())/len(scores),warnings)

def fingerprint_scorecard(scorecard:EvidenceScorecard)->str:
    return hashlib.sha256(json.dumps(scorecard.to_dict(),sort_keys=True,separators=(",",":")).encode()).hexdigest()
