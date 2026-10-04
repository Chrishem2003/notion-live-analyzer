"""Phase 78 — spatial evidence service boundary / API adapter contract."""
from __future__ import annotations
import hashlib,json,re
from typing import Any,Mapping
POLICY_VERSION="phase78-v1";ID_RE=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
def fingerprint(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def _valid_id(v:Any)->bool:return isinstance(v,str) and bool(ID_RE.fullmatch(v))
def service_request(*,request_id:str,operation:str,query:Mapping[str,Any]|None=None)->dict[str,Any]:
 findings=[]
 if not _valid_id(request_id):findings.append({"code":"INVALID_REQUEST_ID"})
 if operation not in {"QUERY","GET_BY_ID","LIST_AOI","LIST_SCENES","LIST_CHANGES"}:findings.append({"code":"UNSUPPORTED_OPERATION"})
 if query is not None and not isinstance(query,Mapping):findings.append({"code":"INVALID_QUERY"})
 if findings:return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":findings}
 payload={"policy_version":POLICY_VERSION,"state":"SERVICE_REQUEST_READY","request_id":request_id,"operation":operation,"query":dict(query or {}),"adapter":"SPATIAL_EVIDENCE_QUERY","read_only":True,"authorization_required":True,"interpretation":"SPATIAL_EVIDENCE_SERVICE_BOUNDARY","environmental_conclusion":None,"regulatory_conclusion":None,"violation":None,"enforcement_action":None}
 payload["request_fingerprint"]=fingerprint(payload);return payload
def adapt_query_result(request:Mapping[str,Any],result:Mapping[str,Any])->dict[str,Any]:
 if request.get("state")!="SERVICE_REQUEST_READY" or request.get("operation") not in {"QUERY","GET_BY_ID","LIST_AOI","LIST_SCENES","LIST_CHANGES"}:return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":[{"code":"INVALID_SERVICE_REQUEST"}]}
 if not isinstance(result,Mapping) or result.get("state")!="QUERY_READY":return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":[{"code":"QUERY_RESULT_NOT_READY"}]}
 out={"policy_version":POLICY_VERSION,"state":"SERVICE_RESPONSE_READY","request_fingerprint":request.get("request_fingerprint"),"result_fingerprint":fingerprint(result),"count":result.get("count",0),"records":list(result.get("records",[])),"read_only":True,"interpretation":"SPATIAL_EVIDENCE_SERVICE_RESPONSE","environmental_conclusion":None,"regulatory_conclusion":None,"violation":None,"enforcement_action":None}
 out["response_fingerprint"]=fingerprint(out);return out
