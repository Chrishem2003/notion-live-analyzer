"""Phase 93 — API audit lifecycle decision reconciliation."""
from __future__ import annotations
from typing import Any,Mapping
from .api_audit_binding import fingerprint
from .api_audit_lifecycle_decision import DECISIONS,POLICY_VERSION as DECISION_POLICY
POLICY_VERSION="phase93-v1"
def reconcile_lifecycle_decisions(*,events:list[Mapping[str,Any]],reconciliations:list[Mapping[str,Any]],lifecycles:list[Mapping[str,Any]],decisions:list[Mapping[str,Any]])->dict[str,Any]:
 event_map={e.get("event_id"):e for e in events}; recon_map={r.get("reconciliation_fingerprint"):r for r in reconciliations}; life_map={l.get("lifecycle_fingerprint"):l for l in lifecycles}
 findings=[]; seen=set()
 for d in decisions:
  did=d.get("decision_id")
  if not isinstance(did,str) or not did: findings.append({"code":"INVALID_DECISION_ID","decision_id":did}); continue
  if did in seen: findings.append({"code":"DUPLICATE_DECISION","decision_id":did})
  seen.add(did)
  if d.get("decision") not in DECISIONS: findings.append({"code":"UNSUPPORTED_DECISION","decision_id":did})
  if d.get("event_id") not in event_map: findings.append({"code":"ORPHAN_EVENT","decision_id":did})
  if d.get("reconciliation_fingerprint") not in recon_map: findings.append({"code":"ORPHAN_RECONCILIATION","decision_id":did})
  if d.get("lifecycle_fingerprint") not in life_map: findings.append({"code":"ORPHAN_LIFECYCLE","decision_id":did})
  event=event_map.get(d.get("event_id")); recon=recon_map.get(d.get("reconciliation_fingerprint")); life=life_map.get(d.get("lifecycle_fingerprint"))
  if event and recon and recon.get("state")!="RECONCILED": findings.append({"code":"RECONCILIATION_NOT_READY","decision_id":did})
  if event and life and life.get("event_id")!=event.get("event_id"): findings.append({"code":"LIFECYCLE_EVENT_MISMATCH","decision_id":did})
  if life and life.get("reconciliation_fingerprint")!=d.get("reconciliation_fingerprint"): findings.append({"code":"LIFECYCLE_SNAPSHOT_MISMATCH","decision_id":did})
  if d.get("decision_fingerprint")!=fingerprint({k:d.get(k) for k in ("event_id","request_id","reconciliation_fingerprint","lifecycle_fingerprint","decision","actor_id","role")}): findings.append({"code":"DECISION_FINGERPRINT_MISMATCH","decision_id":did})
 state="RECONCILED" if not findings else "CONTROL_REQUIRED"
 payload={"policy_version":POLICY_VERSION,"state":state,"finding_count":len(findings),"findings":findings,"decision_count":len(decisions)}
 return dict(payload,reconciliation_fingerprint=fingerprint(payload),interpretation="API_AUDIT_LIFECYCLE_RECONCILIATION",environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None)
