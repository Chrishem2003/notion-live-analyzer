"""Phase 94 — API audit governance casebook."""
from __future__ import annotations
from typing import Any,Mapping
from .api_audit_binding import fingerprint
POLICY_VERSION="phase94-v1"
def build_api_audit_case(*,event:Mapping[str,Any],reconciliation:Mapping[str,Any],lifecycle:Mapping[str,Any],decision:Mapping[str,Any],decision_reconciliation:Mapping[str,Any])->dict[str,Any]:
 required=(event,reconciliation,lifecycle,decision,decision_reconciliation)
 if any(not isinstance(x,Mapping) for x in required): return {"state":"CONTROL_REQUIRED","reason_code":"INVALID_INPUT"}
 if reconciliation.get("state")!="RECONCILED" or decision_reconciliation.get("state")!="RECONCILED": return {"state":"CONTROL_REQUIRED","reason_code":"RECONCILIATION_REQUIRED"}
 if decision.get("event_id")!=event.get("event_id") or lifecycle.get("event_id")!=event.get("event_id"): return {"state":"CONTROL_REQUIRED","reason_code":"EVENT_BINDING_MISMATCH"}
 if decision.get("reconciliation_fingerprint")!=reconciliation.get("reconciliation_fingerprint"): return {"state":"CONTROL_REQUIRED","reason_code":"RECONCILIATION_BINDING_MISMATCH"}
 if decision.get("lifecycle_fingerprint")!=lifecycle.get("lifecycle_fingerprint"): return {"state":"CONTROL_REQUIRED","reason_code":"LIFECYCLE_BINDING_MISMATCH"}
 payload={"event_id":event.get("event_id"),"request_id":event.get("request_id"),"audit_fingerprint":event.get("audit_fingerprint"),"reconciliation_fingerprint":reconciliation.get("reconciliation_fingerprint"),"lifecycle_fingerprint":lifecycle.get("lifecycle_fingerprint"),"decision_id":decision.get("decision_id"),"decision_fingerprint":decision.get("decision_fingerprint"),"decision_reconciliation_fingerprint":decision_reconciliation.get("reconciliation_fingerprint")}
 return dict(payload,case_id="API-CASE-"+fingerprint(payload)[:24],case_fingerprint=fingerprint(payload),state="CASEBOOK_READY",policy_version=POLICY_VERSION,interpretation="API_AUDIT_GOVERNANCE_CASEBOOK",environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None)
