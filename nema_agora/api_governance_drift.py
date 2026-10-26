"""Phase 101 — API governance drift detection and human review trigger."""
from __future__ import annotations
from typing import Any,Mapping
from .api_audit_binding import fingerprint
from .api_governance_snapshot import POLICY_VERSION
POLICY_VERSION="phase101-v1"
def detect_drift(*,baseline:Mapping[str,Any],current:Mapping[str,Any])->dict[str,Any]:
 if not baseline.get("snapshot_id") or not current.get("snapshot_id"): raise ValueError("INVALID_SNAPSHOT")
 if baseline.get("policy_version")!="phase100-v1" or current.get("policy_version")!="phase100-v1": raise ValueError("SNAPSHOT_POLICY_MISMATCH")
 keys=("observatory_state","health_state","coverage_state","control_required_sources","finding_count","counts")
 changes=[{"field":k,"baseline":baseline.get(k),"current":current.get(k)} for k in keys if baseline.get(k)!=current.get(k)]
 drift=bool(changes)
 severity="HIGH" if current.get("health_state")=="CONTROL_REQUIRED" or current.get("observatory_state")=="CONTROL_REQUIRED" else ("MEDIUM" if drift else "NONE")
 payload={"policy_version":POLICY_VERSION,"baseline_snapshot_id":baseline["snapshot_id"],"current_snapshot_id":current["snapshot_id"],"drift_detected":drift,"severity":severity,"changes":changes,"review_required":drift}
 return dict(payload,drift_id="API-DRIFT-"+fingerprint(payload)[:24],drift_fingerprint=fingerprint(payload),state="REVIEW_TRIGGERED" if drift else "NO_DRIFT",interpretation="API_GOVERNANCE_DRIFT_DETECTION",environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None,read_only=True)
