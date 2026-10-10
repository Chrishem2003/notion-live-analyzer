"""Phase 98 — API governance evidence observatory."""
from __future__ import annotations
from typing import Any,Mapping
from .api_audit_binding import fingerprint
POLICY_VERSION="phase98-v1"
def build_observatory(*,events:list[Mapping[str,Any]],reconciliations:list[Mapping[str,Any]],lifecycles:list[Mapping[str,Any]],decisions:list[Mapping[str,Any]],cases:list[Mapping[str,Any]],queue_items:list[Mapping[str,Any]],reviews:list[Mapping[str,Any]],review_reconciliation:Mapping[str,Any])->dict[str,Any]:
 states=[x.get("state") for x in reconciliations]+[review_reconciliation.get("state")]
 control=sum(s=="CONTROL_REQUIRED" for s in states)
 payload={"policy_version":POLICY_VERSION,"counts":{"audit_events":len(events),"reconciliations":len(reconciliations),"lifecycles":len(lifecycles),"decisions":len(decisions),"cases":len(cases),"queued_reviews":len(queue_items),"human_reviews":len(reviews)},"control_required_sources":control,"state":"CONTROL_REQUIRED" if control else "READY_FOR_HUMAN_REVIEW","interpretation":"API_GOVERNANCE_EVIDENCE_OBSERVATORY"}
 return dict(payload,observatory_fingerprint=fingerprint(payload),environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None,read_only=True)
