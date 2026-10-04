"""Phase 55 — NEMA-AGORA platform capability registry."""
from __future__ import annotations
import hashlib,json
from typing import Any,Iterable,Mapping
POLICY_VERSION="phase55-v1"
STATUSES={"IMPLEMENTED","PARTIAL","PLANNED","DEFERRED","BLOCKED"}
def fingerprint(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
DEFAULT_CAPABILITIES=(
 {"capability_id":"observation","name":"Environmental Observation & Reporting","status":"IMPLEMENTED","priority":"CORE","dependencies":[]},
 {"capability_id":"spatial_intelligence","name":"Spatial Intelligence Foundation","status":"PLANNED","priority":"FLAGSHIP","dependencies":["observation"]},
 {"capability_id":"remote_sensing","name":"Sentinel-2 Remote Sensing","status":"PLANNED","priority":"FLAGSHIP","dependencies":["spatial_intelligence"]},
 {"capability_id":"ndvi_ndwi","name":"NDVI / NDWI Analytics","status":"PLANNED","priority":"FLAGSHIP","dependencies":["remote_sensing"]},
 {"capability_id":"spatial_change_evidence","name":"Spatial Change Evidence Engine","status":"PLANNED","priority":"FLAGSHIP","dependencies":["ndvi_ndwi","observation"]},
 {"capability_id":"water_quality","name":"Water Quality Intelligence","status":"PLANNED","priority":"FLAGSHIP","dependencies":["observation"]},
 {"capability_id":"biodiversity_edna","name":"Biodiversity & eDNA Intelligence","status":"PLANNED","priority":"FLAGSHIP","dependencies":["observation"]},
 {"capability_id":"community_gateway","name":"Community USSD / SMS Gateway","status":"PLANNED","priority":"FIELD","dependencies":["observation"]},
 {"capability_id":"community_alerts","name":"Community Alert Engine","status":"PLANNED","priority":"FIELD","dependencies":["community_gateway","human_review"]},
 {"capability_id":"compliance_dashboard","name":"Unified Environmental Analytics Dashboard","status":"PARTIAL","priority":"CORE","dependencies":["observation","spatial_change_evidence","water_quality","biodiversity_edna","community_gateway"]},
 {"capability_id":"governance_evidence","name":"Governance, Evidence & Human Review","status":"IMPLEMENTED","priority":"CORE","dependencies":["observation"]},
 {"capability_id":"ai_evaluation","name":"AI Evaluation & Controlled Shadow","status":"IMPLEMENTED","priority":"ADVANCED","dependencies":["governance_evidence"]},
)
def validate_capabilities(capabilities:Iterable[Mapping[str,Any]]=DEFAULT_CAPABILITIES)->dict[str,Any]:
 rows=[dict(x) for x in capabilities]; ids={str(x.get("capability_id")) for x in rows}; findings=[]
 for row in rows:
  cid=str(row.get("capability_id",""))
  if not cid or not row.get("name"): findings.append({"code":"INVALID_CAPABILITY","capability_id":cid})
  if row.get("status") not in STATUSES: findings.append({"code":"INVALID_STATUS","capability_id":cid})
  for dep in row.get("dependencies",[]) or []:
   if str(dep) not in ids: findings.append({"code":"MISSING_DEPENDENCY","capability_id":cid,"dependency":str(dep)})
 canonical=sorted(findings,key=lambda x:json.dumps(x,sort_keys=True))
 return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED" if canonical else "VALID","capability_count":len(rows),"findings":canonical,"capabilities":sorted(rows,key=lambda x:str(x.get("capability_id",""))),"registry_fingerprint":fingerprint({"capabilities":sorted(rows,key=lambda x:str(x.get("capability_id",""))),"findings":canonical})}
