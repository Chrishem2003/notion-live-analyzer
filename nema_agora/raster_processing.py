"""Phase 72 — governed Sentinel-2 raster processing contract."""
from __future__ import annotations
import hashlib,json,math,re
from typing import Any,Mapping
POLICY_VERSION="phase72-v1"
ID_RE=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
BANDS={"B02","B03","B04","B08"}
def fingerprint(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def _id(v:Any)->bool:return isinstance(v,str) and bool(ID_RE.fullmatch(v))
def validate_band(band:Mapping[str,Any])->dict[str,Any]:
 f=[]
 if not _id(band.get("band_id")):f.append({"code":"INVALID_BAND_ID"})
 if band.get("band") not in BANDS:f.append({"code":"UNSUPPORTED_BAND"})
 if not isinstance(band.get("width"),int) or band["width"]<=0:f.append({"code":"INVALID_WIDTH"})
 if not isinstance(band.get("height"),int) or band["height"]<=0:f.append({"code":"INVALID_HEIGHT"})
 if band.get("dtype") not in {"uint16","float32","float64"}:f.append({"code":"UNSUPPORTED_DTYPE"})
 if band.get("resolution_m") not in {10,20,60}:f.append({"code":"INVALID_RESOLUTION"})
 return {"policy_version":POLICY_VERSION,"state":"VALID" if not f else "CONTROL_REQUIRED","findings":f}
def validate_raster_input(r:Mapping[str,Any])->dict[str,Any]:
 f=[]
 if not _id(r.get("scene_id")):f.append({"code":"INVALID_SCENE_ID"})
 if r.get("crs")!="EPSG:4326":f.append({"code":"UNSUPPORTED_CRS"})
 if not isinstance(r.get("aoi_geometry"),Mapping):f.append({"code":"MISSING_AOI_GEOMETRY"})
 bands=r.get("bands")
 if not isinstance(bands,list) or not bands:f.append({"code":"MISSING_BANDS"})
 else:
  for b in bands:f.extend(validate_band(b)["findings"])
  names=[b.get("band") for b in bands]
  if len(names)!=len(set(names)):f.append({"code":"DUPLICATE_BAND"})
  if not BANDS.issubset(set(names)):f.append({"code":"REQUIRED_BANDS_MISSING"})
 cloud=r.get("cloud_mask_applied")
 if not isinstance(cloud,bool):f.append({"code":"CLOUD_MASK_STATUS_REQUIRED"})
 vf=r.get("valid_fraction")
 if isinstance(vf,bool) or not isinstance(vf,(int,float)) or not 0<=float(vf)<=1:f.append({"code":"INVALID_VALID_FRACTION"})
 return {"policy_version":POLICY_VERSION,"state":"VALID" if not f else "CONTROL_REQUIRED","findings":f,"input_fingerprint":fingerprint(dict(r))}
def build_raster_input(scene_id:str,aoi_geometry:Mapping[str,Any],bands:list[Mapping[str,Any]],*,valid_fraction:float=1.0,cloud_mask_applied:bool=False)->dict[str,Any]:
 r={"scene_id":scene_id,"aoi_geometry":dict(aoi_geometry),"crs":"EPSG:4326","bands":[dict(b) for b in bands],"valid_fraction":valid_fraction,"cloud_mask_applied":cloud_mask_applied}
 c=validate_raster_input(r)
 if c["state"]!="VALID":raise ValueError("Invalid raster input: "+json.dumps(c["findings"],sort_keys=True))
 r["input_fingerprint"]=c["input_fingerprint"];r["policy_version"]=POLICY_VERSION;return r
def process_raster(raster:Mapping[str,Any],*,target_resolution_m:int=10)->dict[str,Any]:
 c=validate_raster_input(raster)
 if c["state"]!="VALID":return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":c["findings"]}
 if target_resolution_m not in {10,20,60}:return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":[{"code":"INVALID_TARGET_RESOLUTION"}]}
 if not raster["cloud_mask_applied"]:return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":[{"code":"CLOUD_MASK_REQUIRED"}]}
 return {"policy_version":POLICY_VERSION,"state":"PROCESSED","scene_id":raster["scene_id"],"aoi_geometry":raster["aoi_geometry"],"target_resolution_m":target_resolution_m,"valid_fraction":raster["valid_fraction"],"bands":sorted(BANDS),"source_fingerprint":c["input_fingerprint"],"processing_fingerprint":fingerprint({"source":c["input_fingerprint"],"target_resolution_m":target_resolution_m}),"environmental_conclusion":None,"regulatory_conclusion":None}
