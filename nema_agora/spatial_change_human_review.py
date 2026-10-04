"""Phase 64 — explicit human review outcomes for spatial-change candidates."""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib,json,re
from typing import Any,Mapping
POLICY_VERSION="phase64-v1"
OUTCOMES={"CONFIRMED_CHANGE","NOT_CONFIRMED","INSUFFICIENT_EVIDENCE","ESCALATED"}
ROLES={"reviewer","coordinator","admin"}
ID_RE=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
SHA_RE=re.compile(r"^[0-9a-f]{64}$")
def fingerprint(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def validate_review(item:Mapping[str,Any],reviewer_id:str,role:str,outcome:str)->dict[str,Any]:
 f=[]
 if not isinstance(item,Mapping) or item.get("queue_state")!="QUEUED":f.append("QUEUE_ITEM_NOT_QUEUED")
 for k in ("review_item_id","candidate_id"):
  if not isinstance(item,Mapping) or not isinstance(item.get(k),str) or not ID_RE.fullmatch(item.get(k,"")):f.append("INVALID_"+k.upper())
 if not isinstance(item,Mapping) or not SHA_RE.fullmatch(str(item.get("record_fingerprint","")).lower()):f.append("INVALID_QUEUE_FINGERPRINT")
 if not isinstance(reviewer_id,str) or not ID_RE.fullmatch(reviewer_id.strip()):f.append("INVALID_REVIEWER_ID")
 if role not in ROLES:f.append("UNAUTHORIZED_REVIEWER_ROLE")
 if outcome not in OUTCOMES:f.append("UNSUPPORTED_REVIEW_OUTCOME")
 return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED" if f else "VALID","findings":[{"code":x} for x in f]}
def create_review_event(*,item:Mapping[str,Any],reviewer_id:str,role:str,outcome:str,notes:str="",reviewed_at:str|None=None)->dict[str,Any]:
 check=validate_review(item,reviewer_id,role,outcome)
 if check["state"]!="VALID":return check
 event={"policy_version":POLICY_VERSION,"review_event_id":"","review_item_id":item["review_item_id"],"candidate_id":item["candidate_id"],"source_queue_fingerprint":item["record_fingerprint"],"reviewer_id":reviewer_id.strip(),"reviewer_role":role,"outcome":outcome,"notes":notes,"reviewed_at":reviewed_at or datetime.now(timezone.utc).isoformat(),"audit_event_type":"SPATIAL_CHANGE_HUMAN_REVIEW","human_decision":True}
 event["review_event_id"]="SPATIAL-REVIEW-"+fingerprint({k:v for k,v in event.items() if k!="review_event_id"})[:24]
 event["event_fingerprint"]=fingerprint(event)
 return event
