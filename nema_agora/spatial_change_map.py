"""Phase 74 — governed spatial change maps from aligned index grids."""
from __future__ import annotations
import hashlib,json,math,re
from typing import Any,Sequence
POLICY_VERSION="phase74-v1"; ID_RE=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
def fingerprint(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def _id(v:Any)->bool:return isinstance(v,str) and bool(ID_RE.fullmatch(v))
def _grid(g:Any)->bool:
 return isinstance(g,(list,tuple)) and bool(g) and all(isinstance(r,(list,tuple)) and r and all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(float(x)) for x in r) for r in g) and len({len(r) for r in g})==1
def build_change_map(*,baseline_scene_id:str,comparison_scene_id:str,aoi_id:str,baseline_indices:dict[str,Sequence[Sequence[float]]],comparison_indices:dict[str,Sequence[Sequence[float]]],thresholds:dict[str,float]|None=None)->dict[str,Any]:
 f=[]
 for name in ("NDVI","NDWI_MCFEETERS","MSAVI2"):
  if name not in baseline_indices or name not in comparison_indices:f.append({"code":"MISSING_INDEX","index":name});continue
  if not _grid(baseline_indices[name]) or not _grid(comparison_indices[name]):f.append({"code":"INVALID_GRID","index":name});continue
  if len(baseline_indices[name])!=len(comparison_indices[name]) or any(len(a)!=len(b) for a,b in zip(baseline_indices[name],comparison_indices[name])):f.append({"code":"GRID_ALIGNMENT_MISMATCH","index":name})
 if not _id(baseline_scene_id) or not _id(comparison_scene_id):f.append({"code":"INVALID_SCENE_ID"})
 if not _id(aoi_id):f.append({"code":"INVALID_AOI_ID"})
 if baseline_scene_id==comparison_scene_id:f.append({"code":"SAME_SCENE"})
 if f:return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":f}
 thresholds=thresholds or {"NDVI":0.2,"NDWI_MCFEETERS":0.2,"MSAVI2":0.2}
 cells=[];summary={"changed_cells":0,"total_cells":len(baseline_indices["NDVI"])*len(baseline_indices["NDVI"][0])}
 for i,row in enumerate(baseline_indices["NDVI"]):
  for j,_ in enumerate(row):
   deltas={n:float(comparison_indices[n][i][j])-float(baseline_indices[n][i][j]) for n in ("NDVI","NDWI_MCFEETERS","MSAVI2")}
   hits={n:abs(d)>=float(thresholds[n]) for n,d in deltas.items()}
   changed=any(hits.values())
   if changed:summary["changed_cells"]+=1
   cells.append({"row":i,"col":j,"delta":deltas,"changed":changed,"reason_codes":[f"{n}_CHANGE_THRESHOLD_MET" for n,h in hits.items() if h]})
 payload={"policy_version":POLICY_VERSION,"state":"MAP_READY","baseline_scene_id":baseline_scene_id,"comparison_scene_id":comparison_scene_id,"aoi_id":aoi_id,"grid_shape":[len(baseline_indices["NDVI"]),len(baseline_indices["NDVI"][0])],"thresholds":thresholds,"cells":cells,"summary":summary,"interpretation":"SPATIAL_CHANGE_MAP_EVIDENCE","environmental_conclusion":None,"regulatory_conclusion":None,"violation":None,"enforcement_action":None}
 payload["map_id"]="MAP-"+fingerprint({"baseline":baseline_scene_id,"comparison":comparison_scene_id,"aoi_id":aoi_id,"cells":cells,"thresholds":thresholds})[:24];payload["fingerprint"]=fingerprint(payload);return payload
