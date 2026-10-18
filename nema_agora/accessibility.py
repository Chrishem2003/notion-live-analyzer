"""Phase 23 community accessibility and participation laboratory.

Records aggregate, non-identifying interaction conditions and accessibility
outcomes. It deliberately excludes names, phone numbers, precise locations,
health data and other personal data.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib, json, uuid

POLICY_VERSION="phase23-v1"
CHANNELS=("WEB","LOW_BANDWIDTH","ASSISTED")
OUTCOMES=("COMPLETED","PARTIAL","ABANDONED")

@dataclass(frozen=True)
class AccessibilityObservation:
    observation_id:str
    scenario_id:str
    channel:str
    outcome:str
    steps_completed:int
    steps_expected:int
    accessibility_barrier:bool
    review_required:bool
    notes:str=""
    created_at:str=""
    policy_version:str=POLICY_VERSION
    def to_dict(self): return asdict(self)

def make_observation(*,scenario_id,channel,outcome,steps_completed,steps_expected,
                     accessibility_barrier,review_required,notes=""):
    channel=channel.upper(); outcome=outcome.upper()
    if channel not in CHANNELS: raise ValueError("unsupported channel")
    if outcome not in OUTCOMES: raise ValueError("unsupported outcome")
    if steps_expected<=0 or not 0<=steps_completed<=steps_expected:
        raise ValueError("invalid completion steps")
    return AccessibilityObservation(
        f"AX-{uuid.uuid4().hex[:10].upper()}",str(scenario_id),channel,outcome,
        int(steps_completed),int(steps_expected),bool(accessibility_barrier),
        bool(review_required),str(notes).strip(),
        datetime.now().astimezone().isoformat(timespec="seconds"))

def fingerprint(rows):
    return hashlib.sha256(json.dumps([r.to_dict() for r in rows],
        sort_keys=True,separators=(",",":")).encode()).hexdigest()

def summarise(rows):
    total=len(rows)
    completed=sum(r.outcome=="COMPLETED" for r in rows)
    barriers=sum(r.accessibility_barrier for r in rows)
    return {
        "policy_version":POLICY_VERSION,"total_observations":total,
        "completion_rate":completed/total if total else 0.0,
        "barrier_rate":barriers/total if total else 0.0,
        "channels":{c:sum(r.channel==c for r in rows) for c in CHANNELS},
        "mean_step_completion":sum(r.steps_completed/r.steps_expected for r in rows)/total if total else 0.0,
        "human_governance_required":True,
        "decision_notice":"Accessibility evidence describes controlled system participation only; it is not demographic inference, environmental truth, regulatory status, NEMA authorization, or production approval."
    }

class AccessibilityStore:
    def __init__(self,database_path):
        import sqlite3
        self.database_path=str(database_path)
        with sqlite3.connect(self.database_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS accessibility_observations(
                observation_id TEXT PRIMARY KEY, scenario_id TEXT NOT NULL,
                channel TEXT NOT NULL, outcome TEXT NOT NULL, steps_completed INTEGER NOT NULL,
                steps_expected INTEGER NOT NULL, accessibility_barrier INTEGER NOT NULL,
                review_required INTEGER NOT NULL, notes TEXT NOT NULL,
                created_at TEXT NOT NULL, policy_version TEXT NOT NULL)""")
    def save(self,row):
        import sqlite3
        with sqlite3.connect(self.database_path) as db:
            db.execute("INSERT INTO accessibility_observations VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (row.observation_id,row.scenario_id,row.channel,row.outcome,row.steps_completed,
                 row.steps_expected,int(row.accessibility_barrier),int(row.review_required),
                 row.notes,row.created_at,row.policy_version))
    def list(self,limit=1000):
        import sqlite3
        with sqlite3.connect(self.database_path) as db:
            db.row_factory=sqlite3.Row
            return [dict(x) for x in db.execute(
                "SELECT * FROM accessibility_observations ORDER BY created_at DESC LIMIT ?",
                (max(1,min(int(limit),2000)),))]
