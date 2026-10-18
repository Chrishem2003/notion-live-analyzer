"""Phase 22 impact measurement laboratory.

Measures workflow effects using controlled, synthetic/consented cases. These
metrics are system-performance evidence, not environmental impact claims.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable
import json, hashlib, uuid
from datetime import datetime

POLICY_VERSION="phase22-v1"
METRICS=("TIME_TO_REVIEW","EVIDENCE_COMPLETENESS","DUPLICATE_DETECTION","REVIEWER_WORKLOAD","CORRECTION_RATE","END_TO_END_SUCCESS")

@dataclass(frozen=True)
class ImpactObservation:
    observation_id:str
    scenario_id:str
    condition:str
    review_seconds:float
    evidence_complete:bool
    duplicate_correct:bool
    reviewer_actions:int
    corrected:bool
    workflow_success:bool
    notes:str=""
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class ImpactSummary:
    summary_id:str
    baseline_count:int
    assisted_count:int
    metrics:dict
    created_at:str
    policy_version:str=POLICY_VERSION
    decision_notice:str="Controlled impact evidence measures system behaviour only; it does not establish environmental impact, environmental truth, regulatory status, NEMA authorization, or production approval."
    def to_dict(self): return asdict(self)

def dataset_fingerprint(observations:Iterable[ImpactObservation])->str:
    payload=[o.to_dict() for o in observations]
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def _rate(values): return sum(bool(v) for v in values)/len(values) if values else 0.0

def summarise_impact(observations:list[ImpactObservation])->ImpactSummary:
    baseline=[o for o in observations if o.condition=="BASELINE"]
    assisted=[o for o in observations if o.condition=="ASSISTED"]
    def group(rows):
        return {
            "n":len(rows),
            "median_review_seconds": sorted([o.review_seconds for o in rows])[len(rows)//2] if rows else None,
            "evidence_completeness_rate":_rate([o.evidence_complete for o in rows]),
            "duplicate_detection_rate":_rate([o.duplicate_correct for o in rows]),
            "mean_reviewer_actions":sum(o.reviewer_actions for o in rows)/len(rows) if rows else None,
            "correction_rate":_rate([o.corrected for o in rows]),
            "end_to_end_success_rate":_rate([o.workflow_success for o in rows]),
        }
    b,a=group(baseline),group(assisted)
    deltas={}
    for k in ("median_review_seconds","evidence_completeness_rate","duplicate_detection_rate","mean_reviewer_actions","correction_rate","end_to_end_success_rate"):
        if b[k] is not None and a[k] is not None: deltas[k]=a[k]-b[k]
    return ImpactSummary(f"IM-{uuid.uuid4().hex[:10].upper()}",len(baseline),len(assisted),{"baseline":b,"assisted":a,"delta_assisted_minus_baseline":deltas},datetime.now().astimezone().isoformat(timespec="seconds"))

class ImpactStore:
    def __init__(self,database_path:str):
        import sqlite3
        self.database_path=str(database_path)
        with sqlite3.connect(self.database_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS impact_observations(
                observation_id TEXT PRIMARY KEY, scenario_id TEXT NOT NULL, condition TEXT NOT NULL,
                review_seconds REAL NOT NULL, evidence_complete INTEGER NOT NULL,
                duplicate_correct INTEGER NOT NULL, reviewer_actions INTEGER NOT NULL,
                corrected INTEGER NOT NULL, workflow_success INTEGER NOT NULL,
                notes TEXT NOT NULL, created_at TEXT NOT NULL, policy_version TEXT NOT NULL)""")
    def save(self,o:ImpactObservation):
        import sqlite3
        with sqlite3.connect(self.database_path) as db:
            db.execute("INSERT INTO impact_observations VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now'),?)",
                (o.observation_id,o.scenario_id,o.condition,o.review_seconds,int(o.evidence_complete),
                 int(o.duplicate_correct),o.reviewer_actions,int(o.corrected),int(o.workflow_success),o.notes,POLICY_VERSION))
    def list(self,limit=1000):
        import sqlite3
        with sqlite3.connect(self.database_path) as db:
            db.row_factory=sqlite3.Row
            return [dict(r) for r in db.execute("SELECT * FROM impact_observations ORDER BY created_at DESC LIMIT ?",(max(1,min(int(limit),2000)),))]

def make_observation(*,scenario_id,condition,review_seconds,evidence_complete,duplicate_correct,reviewer_actions,corrected,workflow_success,notes=""):
    if condition not in ("BASELINE","ASSISTED"): raise ValueError("condition must be BASELINE or ASSISTED")
    if review_seconds<0 or reviewer_actions<0: raise ValueError("metrics cannot be negative")
    return ImpactObservation(f"IO-{uuid.uuid4().hex[:10].upper()}",scenario_id,condition,float(review_seconds),bool(evidence_complete),bool(duplicate_correct),int(reviewer_actions),bool(corrected),bool(workflow_success),notes.strip())
