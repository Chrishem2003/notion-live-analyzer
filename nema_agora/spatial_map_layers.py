"""Phase 76 — governed spatial evidence visualization layers."""
from __future__ import annotations
import hashlib,json,math,re
from typing import Any,Mapping,Sequence
POLICY_VERSION="phase76-v1";ID_RE=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
def fingerprint(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def _id(v:Any)->bool:return isinstance(v,str) and bool(ID_RE.fullmatch(v))
def build_map_layers(*,aoi:Mapping[str,Any],change_map:Mapping[str,Any],priority_items:Sequence[Mapping[str,Any]]=())->dict[str,Any]:
 f=[]
 if not isinstance(aoi,Mapping) or not _id(aoi.get("asset_id")):f.append({"code":"INVALID_AOI"})
 if not isinstance(change_map,Mapping) or change_map.get("state")!="MAP_READY":f.append({"code":"CHANGE_MAP_NOT_READY"})
 if f:return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":f}
 cells=change_map.get("cells",[])
 layers=[
  {"layer_id":"AOI_BOUNDARY","type":"VECTOR","visibility_default":True,"source":"aoi"},
  {"layer_id":"BASELINE_INDEX_SURFACE","type":"RASTER","visibility_default":True,"source_scene":change_map.get("baseline_scene_id")},
  {"layer_id":"COMPARISON_INDEX_SURFACE","type":"RASTER","visibility_default":True,"source_scene":change_map.get("comparison_scene_id")},
  {"layer_id":"CHANGE_EVIDENCE","type":"GRID","visibility_default":True,"cells":[{"row":c.get("row"),"col":c.get("col"),"changed":c.get("changed"),"reason_codes":c.get("reason_codes",[])} for c in cells]},
  {"layer_id":"REVIEW_PRIORITY","type":"VECTOR_OR_GRID","visibility_default":True,"items":[dict(x) for x in priority_items if isinstance(x,Mapping)]},
 ]
 payload={"policy_version":POLICY_VERSION,"state":"LAYERS_READY","aoi_id":aoi["asset_id"],"map_id":change_map.get("map_id"),"layers":layers,"layer_count":len(layers),"interpretation":"SPATIAL_EVIDENCE_VISUALIZATION","environmental_conclusion":None,"regulatory_conclusion":None,"violation":None,"enforcement_action":None}
 payload["fingerprint"]=fingerprint(payload);return payload
