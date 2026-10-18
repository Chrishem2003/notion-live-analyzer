"""Phase 70 — governed Google Earth Engine integration boundary."""
from __future__ import annotations
import hashlib,json,re
from typing import Any,Mapping
POLICY_VERSION="phase70-v1"
PROVIDER="google-earth-engine"
ID_RE=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
def fingerprint(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def validate_request(r:Mapping[str,Any])->dict[str,Any]:
 f=[]
 if not isinstance(r,Mapping): return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":[{"code":"INVALID_REQUEST"}]}
 for k in ("request_id","asset_id","collection"):
  if not isinstance(r.get(k),str) or not r[k].strip():f.append({"code":f"INVALID_{k.upper()}"})
 if isinstance(r.get("request_id"),str) and not ID_RE.fullmatch(r["request_id"]):f.append({"code":"INVALID_REQUEST_ID"})
 if isinstance(r.get("asset_id"),str) and not ID_RE.fullmatch(r["asset_id"]):f.append({"code":"INVALID_ASSET_ID"})
 if r.get("provider")!=PROVIDER:f.append({"code":"INVALID_PROVIDER"})
 if r.get("crs")!="EPSG:4326":f.append({"code":"UNSUPPORTED_CRS"})
 if not isinstance(r.get("geometry"),Mapping):f.append({"code":"MISSING_AOI_GEOMETRY"})
 if not isinstance(r.get("start_date"),str) or not r["start_date"].strip():f.append({"code":"MISSING_START_DATE"})
 if not isinstance(r.get("end_date"),str) or not r["end_date"].strip():f.append({"code":"MISSING_END_DATE"})
 cloud=r.get("max_cloud_cover_pct")
 if isinstance(cloud,bool) or not isinstance(cloud,(int,float)) or not 0<=float(cloud)<=100:f.append({"code":"INVALID_CLOUD_LIMIT"})
 return {"policy_version":POLICY_VERSION,"state":"READY" if not f else "CONTROL_REQUIRED","findings":f,"request_fingerprint":fingerprint(dict(r))}
def build_request(request_id:str,asset_id:str,geometry:Mapping[str,Any],collection:str,start_date:str,end_date:str,*,max_cloud_cover_pct:float=30.0)->dict[str,Any]:
 r={"request_id":request_id,"asset_id":asset_id,"provider":PROVIDER,"collection":collection,"geometry":dict(geometry),"crs":"EPSG:4326","start_date":start_date,"end_date":end_date,"max_cloud_cover_pct":max_cloud_cover_pct}
 c=validate_request(r)
 if c["state"]!="READY":raise ValueError("Invalid GEE request: "+json.dumps(c["findings"],sort_keys=True))
 r["request_fingerprint"]=c["request_fingerprint"];r["policy_version"]=POLICY_VERSION;return r
class EarthEngineProvider:
 provider_name=PROVIDER
 def query(self,request:Mapping[str,Any])->Mapping[str,Any]:
  raise NotImplementedError("Live Earth Engine access is intentionally deferred to a concrete authorized provider.")
def provider_boundary(request:Mapping[str,Any])->dict[str,Any]:
 c=validate_request(request)
 if c["state"]!="READY":return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":c["findings"]}
 return {"policy_version":POLICY_VERSION,"state":"PROVIDER_NOT_CONNECTED","provider":PROVIDER,"request_fingerprint":c["request_fingerprint"],"evidence":None,"authorization_required":True,"environmental_conclusion":None,"regulatory_conclusion":None}
