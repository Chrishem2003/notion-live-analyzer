"""Phase 27 — deterministic, session-safe demonstration dataset utilities."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import hashlib, json

POLICY_VERSION="phase27-v1"

@dataclass(frozen=True)
class DemoDataset:
    dataset_id: str
    version: str
    records: tuple[dict[str, Any], ...]
    synthetic: bool=True
    persistent: bool=False
    safety_notice: str="Synthetic demonstration records only; not environmental truth or official reporting data."

def build_demo_dataset(version="demo-v1") -> DemoDataset:
    records=(
        {"case_id":"DEMO-001","description":"Discarded plastic containers observed near a drainage channel.","latitude":0.3476,"longitude":32.5825,"consent":True},
        {"case_id":"DEMO-002","description":"Uncollected household waste visible beside a community access road.","latitude":0.3500,"longitude":32.5900,"consent":True},
        {"case_id":"DEMO-003","description":"Water appearance changed after heavy rainfall; requires human verification.","latitude":0.3420,"longitude":32.5750,"consent":True},
        {"case_id":"DEMO-004","description":"","latitude":0.3500,"longitude":32.5800,"consent":True},
        {"case_id":"DEMO-005","description":"Possible duplicate of DEMO-001 for reviewer training.","latitude":0.3477,"longitude":32.5826,"consent":True},
    )
    return DemoDataset(_fingerprint({"version":version,"records":records}),version,records)

def _fingerprint(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def validate_demo_dataset(dataset:DemoDataset)->dict[str,Any]:
    return {"dataset_id":dataset.dataset_id,"version":dataset.version,"record_count":len(dataset.records),"synthetic":dataset.synthetic,"persistent":dataset.persistent,"valid":dataset.synthetic and not dataset.persistent}

def serialise_demo_dataset(dataset:DemoDataset)->str:
    return json.dumps({"dataset_id":dataset.dataset_id,"version":dataset.version,"records":dataset.records,"synthetic":dataset.synthetic,"persistent":dataset.persistent,"safety_notice":dataset.safety_notice},sort_keys=True,indent=2)
