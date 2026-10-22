"""Phase 66 — deterministic spatial review evidence casebook and provenance."""
from __future__ import annotations
import hashlib,json,re
from typing import Any,Mapping
POLICY_VERSION="phase66-v1"
ID_RE=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
SHA_RE=re.compile(r"^[0-9a-f]{64}$")
OUTCOMES=frozenset({"CONFIRMED_CHANGE","NOT_CONFIRMED","INSUFFICIENT_EVIDENCE","ESCALATED"})
def fingerprint(v:Any)->str:
 return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def _id(v:Any)->bool:return isinstance(v,str) and bool(ID_RE.fullmatch(v.strip()))
def _sha(v:Any)->bool:return isinstance(v,str) and bool(SHA_RE.fullmatch(v.strip().lower()))
def _event_fp(e:Mapping[str,Any])->str:return fingerprint({k:v for k,v in e.items() if k!="event_fingerprint"})
def build_spatial_review_casebook(queue_items:list[Mapping[str,Any]],audit_events:list[Mapping[str,Any]],reconciliation:Mapping[str,Any])->dict[str,Any]:
 findings=[];cases=[]
 if not isinstance(reconciliation,Mapping): findings.append({"code":"INVALID_RECONCILIATION"}); reconciliation={}
 if reconciliation.get("policy_version")!="phase65-v1":findings.append({"code":"WRONG_RECONCILIATION_POLICY"})
 recon_fp=str(reconciliation.get("reconciliation_fingerprint","")).strip().lower()
 if not _sha(recon_fp):findings.append({"code":"INVALID_RECONCILIATION_FINGERPRINT"})
 if not isinstance(queue_items,list) or not isinstance(audit_events,list):
  findings.append({"code":"INVALID_CASEBOOK_INPUT"});return _result(findings,cases,recon_fp)
 audit_by={}
 for e in audit_events:
  if isinstance(e,Mapping) and _id(e.get("review_item_id")):audit_by.setdefault(e["review_item_id"],[]).append(e)
 for item in queue_items:
  if not isinstance(item,Mapping) or not _id(item.get("review_item_id")):findings.append({"code":"INVALID_QUEUE_ARTIFACT"});continue
  item_id=item["review_item_id"];events=audit_by.get(item_id,[])
  if len(events)!=1:findings.append({"code":"CASE_NOT_UNIQUELY_REVIEWED","review_item_id":item_id});continue
  e=events[0];qfp=str(item.get("record_fingerprint","")).strip().lower();efp=str(e.get("event_fingerprint","")).strip().lower()
  if not _sha(qfp):findings.append({"code":"INVALID_QUEUE_FINGERPRINT","review_item_id":item_id});continue
  if not _sha(efp) or _event_fp(e)!=efp:findings.append({"code":"AUDIT_EVENT_FINGERPRINT_MISMATCH","review_item_id":item_id})
  if str(e.get("source_queue_fingerprint","")).strip().lower()!=qfp:findings.append({"code":"QUEUE_BINDING_MISMATCH","review_item_id":item_id})
  if e.get("candidate_id")!=item.get("candidate_id"):findings.append({"code":"CANDIDATE_IDENTITY_MISMATCH","review_item_id":item_id})
  if e.get("outcome") not in OUTCOMES:findings.append({"code":"INVALID_REVIEW_OUTCOME","review_item_id":item_id})
  case={"policy_version":POLICY_VERSION,"case_id":"","review_item_id":item_id,"candidate_id":item.get("candidate_id"),"review_outcome":e.get("outcome"),
   "queue_artifact":{"record_fingerprint":qfp,"source_candidate_fingerprint":item.get("source_candidate_fingerprint"),"priority_score":item.get("priority_score"),"priority_tier":item.get("priority_tier"),"reason_codes":item.get("reason_codes"),"spatial":item.get("spatial"),"created_at":item.get("created_at")},
   "review_artifact":{"review_event_id":e.get("review_event_id"),"event_fingerprint":efp,"source_queue_fingerprint":e.get("source_queue_fingerprint"),"reviewer_id":e.get("reviewer_id"),"reviewer_role":e.get("reviewer_role"),"reviewed_at":e.get("reviewed_at"),"audit_event_type":e.get("audit_event_type"),"human_decision":e.get("human_decision")},
   "provenance":{"queue_fingerprint":qfp,"audit_event_fingerprint":efp,"reconciliation_fingerprint":recon_fp},
   "interpretation":{"status":"HUMAN_REVIEW_EVIDENCE","environmental_conclusion":None,"regulatory_conclusion":None,"violation":None,"enforcement_action":None}}
  case["case_id"]="SPATIAL-CASE-"+fingerprint({k:v for k,v in case.items() if k!="case_id"})[:24];case["case_fingerprint"]=fingerprint(case);cases.append(case)
 cases.sort(key=lambda x:x["case_id"]);return _result(findings,cases,recon_fp)
def _result(findings,cases,recon_fp):
 findings=[dict(x,**({"fingerprint":fingerprint(x)} if "fingerprint" not in x else {})) for x in findings]
 findings.sort(key=lambda x:(x.get("code",""),x.get("review_item_id",""),x["fingerprint"]))
 result={"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED" if findings else ("CASEBOOK_READY" if cases else "NO_CASES"),"case_count":len(cases),"cases":cases,"findings":findings,"reconciliation_fingerprint":recon_fp,"interpretation":{"status":"HUMAN_REVIEW_REQUIRED" if findings else ("EVIDENCE_CASEBOOK_READY" if cases else "NO_CASES"),"environmental_conclusion":None,"regulatory_conclusion":None,"violation":None,"enforcement_action":None}}
 result["casebook_fingerprint"]=fingerprint(result);return result
