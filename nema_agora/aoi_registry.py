"""Phase 69 — governed AOI/environmental asset registry contract."""
from __future__ import annotations
import hashlib,json,re
from datetime import datetime
from typing import Any,Mapping
POLICY_VERSION="phase69-v1"
ID_RE=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
SHA_RE=re.compile(r"^[0-9a-f]{64}$")
ASSET_TYPES={"DISTRICT","WETLAND","WATERSHED","PROTECTED_AREA","FOREST_RESERVE","LAKE","RIVER","RIVER_BUFFER","LAKESHORE_ZONE","CUSTOM"}
STATUSES={"ACTIVE","INACTIVE","PROPOSED"}
def fingerprint(v:Any)->str:
 return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def _id(v:Any)->bool:return isinstance(v,str) and bool(ID_RE.fullmatch(v.strip()))
def _sha(v:Any)->bool:return isinstance(v,str) and bool(SHA_RE.fullmatch(v.strip().lower()))
def _time(v:Any)->bool:
 if not isinstance(v,str):return False
 try: datetime.fromisoformat(v.replace("Z","+00:00")); return True
 except ValueError:return False
def validate_asset(a:Mapping[str,Any])->dict[str,Any]:
 f=[]
 if not isinstance(a,Mapping): return {"state":"CONTROL_REQUIRED","findings":[{"code":"INVALID_ASSET"}]}
 for k in ("asset_id","name","source"):
  if not isinstance(a.get(k),str) or not a.get(k).strip(): f.append({"code":f"INVALID_{k.upper()}"})
 if not _id(a.get("asset_id")): f.append({"code":"INVALID_ASSET_ID"})
 if a.get("asset_type") not in ASSET_TYPES: f.append({"code":"INVALID_ASSET_TYPE"})
 if a.get("status") not in STATUSES: f.append({"code":"INVALID_STATUS"})
 if a.get("crs")!="EPSG:4326": f.append({"code":"UNSUPPORTED_CRS"})
 g=a.get("geometry")
 if not isinstance(g,Mapping) or g.get("type") not in {"Point","Polygon","MultiPolygon"}: f.append({"code":"INVALID_GEOMETRY"})
 if not isinstance(a.get("source_reference"),str) or not a["source_reference"].strip(): f.append({"code":"MISSING_SOURCE_REFERENCE"})
 for k in ("effective_from","effective_to"):
  if a.get(k) is not None and not _time(a[k]): f.append({"code":f"INVALID_{k.upper()}"})
 return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED" if f else "VALID","findings":f}
def build_asset(asset_id:str,name:str,asset_type:str,geometry:Mapping[str,Any],source:str,source_reference:str,*,status="PROPOSED",effective_from=None,effective_to=None,version=1,metadata=None)->dict[str,Any]:
 row={"asset_id":asset_id,"name":name,"asset_type":asset_type,"geometry":dict(geometry),"crs":"EPSG:4326","source":source,"source_reference":source_reference,"effective_from":effective_from,"effective_to":effective_to,"version":version,"status":status,"metadata":dict(metadata or {})}
 c=validate_asset(row)
 if c["state"]!="VALID": raise ValueError("Invalid environmental asset: "+json.dumps(c["findings"],sort_keys=True))
 row["asset_fingerprint"]=fingerprint(row); row["policy_version"]=POLICY_VERSION
 return row
def validate_registry(assets:list[Mapping[str,Any]])->dict[str,Any]:
 f=[];seen=set()
 if not isinstance(assets,list): return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":[{"code":"INVALID_ASSETS"}]}
 for a in assets:
  c=validate_asset(a); f.extend(c["findings"]); aid=a.get("asset_id")
  if aid in seen:f.append({"code":"DUPLICATE_ASSET_ID","asset_id":aid})
  seen.add(aid)
  if a.get("asset_fingerprint") is not None and not _sha(a["asset_fingerprint"]): f.append({"code":"INVALID_ASSET_FINGERPRINT","asset_id":aid})
 return {"policy_version":POLICY_VERSION,"state":"REGISTRY_READY" if not f else "CONTROL_REQUIRED","findings":f,"asset_count":len(assets)}
def query_assets(assets:list[Mapping[str,Any]],*,asset_type=None,status=None)->list[dict[str,Any]]:
 c=validate_registry(assets)
 if c["state"]!="REGISTRY_READY": raise ValueError("Registry requires control")
 return sorted([dict(a) for a in assets if (asset_type is None or a["asset_type"]==asset_type) and (status is None or a["status"]==status)],key=lambda x:x["asset_id"])
