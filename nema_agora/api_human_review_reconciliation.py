"""Phase 97 — API human review reconciliation and evidence integrity."""
from __future__ import annotations
from typing import Any,Mapping
from .api_audit_binding import fingerprint
from .api_governance_human_review import OUTCOMES
POLICY_VERSION="phase97-v1"
def review_audit_fingerprint(a:Mapping[str,Any])->str:
 return fingerprint({k:a.get(k) for k in ("review_id","case_id","case_fingerprint","request_id","reviewer_actor_id","reviewer_role","outcome","reviewed_at")})
def reconcile_reviews(*,queue_items:list[Mapping[str,Any]],cases:list[Mapping[str,Any]],audits:list[Mapping[str,Any]])->dict[str,Any]:
 q={x.get("review_id"):x for x in queue_items}; c={x.get("case_id"):x for x in cases}; findings=[];seen=set()
 for a in audits:
  rid=a.get("review_id")
  if rid in seen:findings.append({"code":"DUPLICATE_REVIEW_AUDIT","review_id":rid})
  seen.add(rid)
  item=q.get(rid);case=c.get(a.get("case_id"))
  if not item:findings.append({"code":"ORPHAN_REVIEW","review_id":rid})
  if not case:findings.append({"code":"ORPHAN_CASE","review_id":rid})
  if item and a.get("case_fingerprint")!=item.get("case_fingerprint"):findings.append({"code":"QUEUE_FINGERPRINT_MISMATCH","review_id":rid})
  if case and a.get("case_fingerprint")!=case.get("case_fingerprint"):findings.append({"code":"CASE_FINGERPRINT_MISMATCH","review_id":rid})
  if a.get("outcome") not in OUTCOMES:findings.append({"code":"INVALID_OUTCOME","review_id":rid})
  if a.get("audit_fingerprint")!=review_audit_fingerprint(a):findings.append({"code":"REVIEW_AUDIT_FINGERPRINT_MISMATCH","review_id":rid})
  if item and a.get("request_id")!=item.get("request_id"):findings.append({"code":"REQUEST_ID_MISMATCH","review_id":rid})
 state="RECONCILED" if not findings else "CONTROL_REQUIRED"
 payload={"policy_version":POLICY_VERSION,"state":state,"finding_count":len(findings),"findings":findings,"audit_count":len(audits)}
 return dict(payload,reconciliation_fingerprint=fingerprint(payload),interpretation="API_HUMAN_REVIEW_RECONCILIATION",environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None)
