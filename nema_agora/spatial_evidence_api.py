"""Phase 77 — governed spatial evidence query/API surface."""
from __future__ import annotations
import hashlib,json,re
from typing import Any,Mapping,Sequence
POLICY_VERSION="phase77-v1";ID_RE=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
def fingerprint(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def _id(v:Any)->bool:return isinstance(v,str) and bool(ID_RE.fullmatch(v))
def _match(x:Mapping[str,Any],q:Mapping[str,Any])->bool:
 for k in ("aoi_id","scene_id","candidate_id","review_status"):
  if q.get(k) is not None and x.get(k)!=q[k]: return False
 return True
def query_spatial_evidence(records:Sequence[Mapping[str,Any]],*,aoi_id:str|None=None,scene_id:str|None=None,candidate_id:str|None=None,review_status:str|None=None,observed_from:str|None=None,observed_to:str|None=None,limit:int=100)->dict[str,Any]:
 if limit<1 or limit>500: return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":[{"code":"INVALID_LIMIT"}]}
 if any(v is not None and not _id(v) for v in (aoi_id,scene_id,candidate_id,review_status)): return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":[{"code":"INVALID_QUERY_ID"}]}
 q={"aoi_id":aoi_id,"scene_id":scene_id,"candidate_id":candidate_id,"review_status":review_status}
 selected=[]
 for r in records:
  if not isinstance(r,Mapping) or not _match(r,q): continue
  if observed_from and str(r.get("observed_at",""))<observed_from: continue
  if observed_to and str(r.get("observed_at",""))>observed_to: continue
  selected.append(dict(r))
 selected.sort(key=lambda r:(str(r.get("observed_at","")),str(r.get("record_id",r.get("candidate_id","")))))
 selected=selected[:limit]
 out={"policy_version":POLICY_VERSION,"state":"QUERY_READY","query":q,"observed_from":observed_from,"observed_to":observed_to,"count":len(selected),"records":selected,"interpretation":"SPATIAL_EVIDENCE_QUERY","environmental_conclusion":None,"regulatory_conclusion":None,"violation":None,"enforcement_action":None}
 out["fingerprint"]=fingerprint(out);return out
