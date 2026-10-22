from __future__ import annotations
import hashlib,json,re
from datetime import datetime
from typing import Any,Mapping
POLICY_VERSION="phase67-v1"
ID_RE=re.compile(r"^[A-Za-z0-9._:-]{1,128}$"); SHA_RE=re.compile(r"^[0-9a-f]{64}$")
def fingerprint(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def _id(v:Any)->bool:return isinstance(v,str) and bool(ID_RE.fullmatch(v.strip()))
def _sha(v:Any)->bool:return isinstance(v,str) and bool(SHA_RE.fullmatch(v.strip().lower()))
def _time(v:Any)->bool:
 if not isinstance(v,str):return False
 try: datetime.fromisoformat(v.replace("Z","+00:00"));return True
 except ValueError:return False
def validate_case(case:Mapping[str,Any])->dict[str,Any]:
 f=[]
 if not isinstance(case,Mapping):return {"state":"CONTROL_REQUIRED","findings":[{"code":"INVALID_CASE"}]}
 for k in ("case_id","candidate_id"):
  if not _id(case.get(k)):f.append({"code":f"INVALID_{k.upper()}"})
 if not _sha(case.get("case_fingerprint")):f.append({"code":"INVALID_CASE_FINGERPRINT"})
 qa=case.get("queue_artifact")
 sp=qa.get("spatial") if isinstance(qa,Mapping) else None
 if not isinstance(sp,Mapping) or not _id(sp.get("aoi_id")) or not _id(sp.get("grid_id")):f.append({"code":"INVALID_SPATIAL_IDENTITY"})
 return {"state":"CONTROL_REQUIRED" if f else "VALID","findings":f}
def build_longitudinal_record(case:Mapping[str,Any],*,observed_at:str,sequence:int,previous_record_fingerprint:str|None=None)->dict[str,Any]:
 f=list(validate_case(case)["findings"])
 if not _time(observed_at):f.append({"code":"INVALID_OBSERVED_AT"})
 if not isinstance(sequence,int) or isinstance(sequence,bool) or sequence<1:f.append({"code":"INVALID_SEQUENCE"})
 if previous_record_fingerprint is not None and not _sha(previous_record_fingerprint):f.append({"code":"INVALID_PREVIOUS_FINGERPRINT"})
 if f:return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":f}
 p={"policy_version":POLICY_VERSION,"record_id":"","case_id":case["case_id"],"candidate_id":case["candidate_id"],"observed_at":observed_at,"sequence":sequence,"previous_record_fingerprint":previous_record_fingerprint,"case_fingerprint":case["case_fingerprint"],"spatial_identity":case["queue_artifact"]["spatial"],"review_outcome":case.get("review_outcome"),"provenance":case["provenance"],"interpretation":{"status":"LONGITUDINAL_EVIDENCE","environmental_conclusion":None,"regulatory_conclusion":None,"violation":None,"enforcement_action":None}}
 p["record_id"]="SPATIAL-HISTORY-"+fingerprint({k:v for k,v in p.items() if k!="record_id"})[:24];p["record_fingerprint"]=fingerprint(p)
 return {"policy_version":POLICY_VERSION,"state":"VALID","record":p}
def build_timeline(records:list[Mapping[str,Any]])->dict[str,Any]:
 if not isinstance(records,list):return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":[{"code":"INVALID_RECORDS"}]}
 f=[];seen=set();ordered=[]
 for r in records:
  if not isinstance(r,Mapping) or not _sha(r.get("record_fingerprint")):f.append({"code":"INVALID_HISTORY_RECORD"});continue
  if r.get("record_id") in seen:f.append({"code":"DUPLICATE_HISTORY_RECORD","record_id":r.get("record_id")});continue
  seen.add(r.get("record_id"));ordered.append(r)
 ordered.sort(key=lambda x:(x.get("observed_at",""),x.get("sequence",0),x.get("record_id","")))
 for i,r in enumerate(ordered):
  if i and r.get("previous_record_fingerprint")!=ordered[i-1].get("record_fingerprint"):f.append({"code":"HISTORY_CHAIN_MISMATCH","record_id":r.get("record_id")})
 result={"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED" if f else ("TIMELINE_READY" if ordered else "NO_HISTORY"),"records":ordered,"findings":f}
 result["timeline_fingerprint"]=fingerprint(result);return result
