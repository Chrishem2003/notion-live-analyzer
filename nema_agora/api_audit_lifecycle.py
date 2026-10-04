"""Phase 91 — API audit lifecycle and retention governance."""
from __future__ import annotations
from datetime import datetime,timezone
from typing import Any,Mapping
from .api_audit_binding import fingerprint
POLICY_VERSION="phase91-v1"
STATES={"RECORDED","RECONCILED","REVIEW_REQUIRED","RETAINED","EXPIRED"}
DECISIONS={"RECONCILE","REQUEST_REVIEW","RETAIN","EXPIRE"}
def _time(value:str)->datetime:
 return datetime.fromisoformat(value.replace("Z","+00:00"))
def evaluate_lifecycle(event:Mapping[str,Any], reconciliation:Mapping[str,Any], *, now:str, retention_days:int=365)->dict[str,Any]:
 if not isinstance(event,Mapping) or not isinstance(reconciliation,Mapping): return {"state":"CONTROL_REQUIRED","reason_code":"INVALID_INPUT"}
 if event.get("state")!="RECORDED" or reconciliation.get("state")!="RECONCILED": return {"state":"CONTROL_REQUIRED","reason_code":"RECONCILIATION_REQUIRED"}
 try:
  occurred=_time(str(event["occurred_at"])); current=_time(now)
 except (KeyError,ValueError): return {"state":"CONTROL_REQUIRED","reason_code":"INVALID_TIMESTAMP"}
 if current<occurred or not isinstance(retention_days,int) or retention_days<1: return {"state":"CONTROL_REQUIRED","reason_code":"INVALID_RETENTION_POLICY"}
 age=(current-occurred).total_seconds()
 state="EXPIRED" if age>retention_days*86400 else "RETAINED"
 payload={"event_id":event.get("event_id"),"request_id":event.get("request_id"),"reconciliation_fingerprint":reconciliation.get("reconciliation_fingerprint"),"state":state,"retention_days":retention_days,"evaluated_at":now}
 return dict(payload,lifecycle_fingerprint=fingerprint(payload),policy_version=POLICY_VERSION,interpretation="API_AUDIT_LIFECYCLE",environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None)
