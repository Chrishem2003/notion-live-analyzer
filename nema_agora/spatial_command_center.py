"""Phase 75 — governed spatial command-center view model."""
from __future__ import annotations
import hashlib,json
from typing import Any,Mapping,Sequence
POLICY_VERSION="phase75-v1"
def fingerprint(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def build_command_center(*,aoi:Mapping[str,Any],change_map:Mapping[str,Any],review_items:Sequence[Mapping[str,Any]]=())->dict[str,Any]:
 findings=[]
 if not isinstance(aoi,Mapping) or not aoi.get("asset_id"):findings.append({"code":"INVALID_AOI"})
 if not isinstance(change_map,Mapping) or change_map.get("state")!="MAP_READY":findings.append({"code":"CHANGE_MAP_NOT_READY"})
 if findings:return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":findings}
 cells=change_map.get("cells",[])
 changed=[c for c in cells if c.get("changed") is True]
 queue=[dict(x) for x in review_items if isinstance(x,Mapping)]
 payload={"policy_version":POLICY_VERSION,"state":"COMMAND_CENTER_READY","aoi":{"asset_id":aoi["asset_id"],"name":aoi.get("name"),"asset_type":aoi.get("asset_type")},"scenes":{"baseline":change_map.get("baseline_scene_id"),"comparison":change_map.get("comparison_scene_id")},"map":{"map_id":change_map.get("map_id"),"grid_shape":change_map.get("grid_shape"),"changed_cells":len(changed),"total_cells":len(cells),"summary":change_map.get("summary",{})},"review_queue":{"items":queue,"count":len(queue)},"interpretation":"SPATIAL_COMMAND_CENTER_EVIDENCE","environmental_conclusion":None,"regulatory_conclusion":None,"violation":None,"enforcement_action":None}
 payload["fingerprint"]=fingerprint(payload);return payload
