"""Phase 71 — governed Sentinel-2 acquisition orchestration contract."""
from __future__ import annotations
import datetime as dt
import hashlib,json,re
from typing import Any,Mapping
POLICY_VERSION="phase71-v1"
ID_RE=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
COLLECTIONS={"COPERNICUS/S2_SR_HARMONIZED","COPERNICUS/S2_HARMONIZED","S2MSI_L2A","S2MSI_L1C"}
def fingerprint(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def _id(v:Any)->bool:return isinstance(v,str) and bool(ID_RE.fullmatch(v))
def _date(v:Any)->bool:
 if not isinstance(v,str) or not v.strip():return False
 try: dt.date.fromisoformat(v); return True
 except ValueError:return False
def validate_acquisition_request(r:Mapping[str,Any])->dict[str,Any]:
 f=[]
 for k in ("request_id","asset_id","collection","start_date","end_date"):
  if not isinstance(r.get(k),str) or not r[k].strip():f.append({"code":f"INVALID_{k.upper()}"})
 for k in ("request_id","asset_id"):
  if isinstance(r.get(k),str) and not _id(r[k]):f.append({"code":f"INVALID_{k.upper()}"})
 if r.get("collection") not in COLLECTIONS:f.append({"code":"UNSUPPORTED_COLLECTION"})
 if not _date(r.get("start_date")):f.append({"code":"INVALID_START_DATE"})
 if not _date(r.get("end_date")):f.append({"code":"INVALID_END_DATE"})
 if _date(r.get("start_date")) and _date(r.get("end_date")) and r["start_date"]>r["end_date"]:f.append({"code":"DATE_RANGE_REVERSED"})
 cloud=r.get("max_cloud_cover_pct",30)
 if isinstance(cloud,bool) or not isinstance(cloud,(int,float)) or not 0<=float(cloud)<=100:f.append({"code":"INVALID_CLOUD_LIMIT"})
 if not isinstance(r.get("aoi_geometry"),Mapping):f.append({"code":"MISSING_AOI_GEOMETRY"})
 return {"policy_version":POLICY_VERSION,"state":"READY" if not f else "CONTROL_REQUIRED","findings":f,"request_fingerprint":fingerprint(dict(r))}
def build_acquisition_request(request_id:str,asset_id:str,aoi_geometry:Mapping[str,Any],collection:str,start_date:str,end_date:str,*,max_cloud_cover_pct:float=30.0)->dict[str,Any]:
 r={"request_id":request_id,"asset_id":asset_id,"aoi_geometry":dict(aoi_geometry),"crs":"EPSG:4326","collection":collection,"start_date":start_date,"end_date":end_date,"max_cloud_cover_pct":max_cloud_cover_pct}
 c=validate_acquisition_request(r)
 if c["state"]!="READY":raise ValueError("Invalid acquisition request: "+json.dumps(c["findings"],sort_keys=True))
 r["request_fingerprint"]=c["request_fingerprint"];r["policy_version"]=POLICY_VERSION;return r
class Sentinel2AcquisitionProvider:
 provider_name="google-earth-engine"
 def search(self,request:Mapping[str,Any])->list[Mapping[str,Any]]:
  raise NotImplementedError("Authorized live Sentinel-2 provider must implement search().")
def acquisition_boundary(request:Mapping[str,Any])->dict[str,Any]:
 c=validate_acquisition_request(request)
 if c["state"]!="READY":return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":c["findings"]}
 return {"policy_version":POLICY_VERSION,"state":"ACQUISITION_NOT_CONNECTED","provider":"google-earth-engine","request_fingerprint":c["request_fingerprint"],"scenes":[],"authorization_required":True,"environmental_conclusion":None,"regulatory_conclusion":None}
def validate_scene_list(scenes:list[Mapping[str,Any]])->dict[str,Any]:
 f=[];ids=set()
 if not isinstance(scenes,list):return {"state":"CONTROL_REQUIRED","findings":[{"code":"INVALID_SCENE_LIST"}]}
 for s in scenes:
  sid=s.get("scene_id")
  if not _id(sid):f.append({"code":"INVALID_SCENE_ID"})
  if sid in ids:f.append({"code":"DUPLICATE_SCENE_ID","scene_id":sid})
  ids.add(sid)
  if s.get("provider")!="google-earth-engine":f.append({"code":"INVALID_SCENE_PROVIDER","scene_id":sid})
 return {"policy_version":POLICY_VERSION,"state":"SCENES_VALID" if not f else "CONTROL_REQUIRED","findings":f,"scene_count":len(scenes)}
