"""Phase 99 — API governance evidence coverage and health."""
from __future__ import annotations
from typing import Any,Mapping
from .api_audit_binding import fingerprint
POLICY_VERSION="phase99-v1"
REQUIRED=("audit_events","reconciliations","lifecycles","decisions","cases","queued_reviews","human_reviews","review_reconciliation")
def evaluate_health(observatory:Mapping[str,Any], *, minimum_counts:Mapping[str,int]|None=None)->dict[str,Any]:
 minimum_counts=dict(minimum_counts or {k:1 for k in REQUIRED})
 counts=observatory.get("counts") if isinstance(observatory.get("counts"),Mapping) else {}
 findings=[]
 for key in REQUIRED:
  if not isinstance(counts.get(key),int) or counts.get(key,0)<minimum_counts.get(key,1): findings.append({"code":"COVERAGE_GAP","component":key,"observed":counts.get(key),"required":minimum_counts.get(key,1)})
 if observatory.get("state")=="CONTROL_REQUIRED": findings.append({"code":"OBSERVATORY_CONTROL_REQUIRED"})
 payload={"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED" if findings else "HEALTHY","coverage_state":"INCOMPLETE" if findings else "COMPLETE","finding_count":len(findings),"findings":findings,"counts":dict(counts)}
 return dict(payload,health_fingerprint=fingerprint(payload),interpretation="API_GOVERNANCE_EVIDENCE_HEALTH",environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None,read_only=True)
