"""Phase 90 — end-to-end API audit reconciliation."""
from __future__ import annotations
from typing import Any,Mapping
from .api_audit_binding import fingerprint
from .api_audit_registry import event_fingerprint,validate_event
POLICY_VERSION="phase90-v1"
def reconcile_api_audit(events:list[Mapping[str,Any]], expected_request_ids:list[str]|None=None)->dict[str,Any]:
 expected=list(dict.fromkeys(expected_request_ids or [])); findings=[]
 seen_events=set(); seen_requests=set()
 for event in events:
  try: validate_event(event)
  except ValueError: findings.append({"code":"INVALID_EVENT","event_id":event.get("event_id")}); continue
  eid=event["event_id"]
  if eid in seen_events: findings.append({"code":"DUPLICATE_EVENT","event_id":eid})
  seen_events.add(eid); seen_requests.add(event["request_id"])
  if event.get("audit_fingerprint")!=event_fingerprint(event): findings.append({"code":"FINGERPRINT_MISMATCH","event_id":eid})
 for req in expected:
  if req not in seen_requests: findings.append({"code":"MISSING_REQUEST_AUDIT","request_id":req})
 state="RECONCILED" if not findings else "CONTROL_REQUIRED"
 payload={"policy_version":POLICY_VERSION,"state":state,"finding_count":len(findings),"findings":findings,"expected_request_ids":expected,"event_count":len(events)}
 return dict(payload,reconciliation_fingerprint=fingerprint(payload),interpretation="API_AUDIT_RECONCILIATION",environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None)
