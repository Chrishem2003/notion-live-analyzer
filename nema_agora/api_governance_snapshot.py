"""Phase 100 — API governance evidence snapshot and baseline."""
from __future__ import annotations
from typing import Any,Mapping
from .api_audit_binding import fingerprint
POLICY_VERSION="phase100-v1"
def build_snapshot(*,observatory:Mapping[str,Any],health:Mapping[str,Any],captured_at:str)->dict[str,Any]:
 if not isinstance(captured_at,str) or not captured_at.strip(): raise ValueError("INVALID_CAPTURE_TIME")
 if not isinstance(observatory,Mapping) or not isinstance(health,Mapping): raise ValueError("INVALID_SNAPSHOT_INPUT")
 payload={"policy_version":POLICY_VERSION,"captured_at":captured_at,"observatory_state":observatory.get("state"),"health_state":health.get("state"),"coverage_state":health.get("coverage_state"),"counts":dict(observatory.get("counts",{})),"control_required_sources":observatory.get("control_required_sources",0),"finding_count":health.get("finding_count",0)}
 return dict(payload,snapshot_id="API-SNAPSHOT-"+fingerprint(payload)[:24],snapshot_fingerprint=fingerprint(payload),interpretation="API_GOVERNANCE_EVIDENCE_SNAPSHOT",environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None,read_only=True)
def diff_snapshots(baseline:Mapping[str,Any],current:Mapping[str,Any])->dict[str,Any]:
 if baseline.get("policy_version")!=POLICY_VERSION or current.get("policy_version")!=POLICY_VERSION: raise ValueError("POLICY_MISMATCH")
 keys=("observatory_state","health_state","coverage_state","control_required_sources","finding_count","counts")
 changes=[{"field":k,"baseline":baseline.get(k),"current":current.get(k)} for k in keys if baseline.get(k)!=current.get(k)]
 payload={"baseline_snapshot_id":baseline.get("snapshot_id"),"current_snapshot_id":current.get("snapshot_id"),"changed":bool(changes),"changes":changes}
 return dict(payload,diff_fingerprint=fingerprint(payload),interpretation="API_GOVERNANCE_SNAPSHOT_DIFF",environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None,read_only=True)
