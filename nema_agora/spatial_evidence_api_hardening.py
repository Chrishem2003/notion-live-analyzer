"""Phase 83 — persistent spatial evidence query API hardening."""
from __future__ import annotations
from typing import Any,Mapping
from nema_agora.spatial_evidence_service import service_request,adapt_query_result
from nema_agora.spatial_evidence_sqlite_repository import SQLiteSpatialEvidenceRepository
POLICY_VERSION="phase83-v1"
def query_persistent_evidence(*,database_path:str,request_id:str,query:Mapping[str,Any]|None=None,limit:int=100)->dict[str,Any]:
    if not isinstance(limit,int) or isinstance(limit,bool) or limit<1 or limit>500: return {"http_status":400,"body":{"state":"CONTROL_REQUIRED","reason_code":"INVALID_LIMIT","policy_version":POLICY_VERSION}}
    req=service_request(request_id=request_id,operation="QUERY",query=query)
    if req["state"]!="SERVICE_REQUEST_READY": return {"http_status":400,"body":req}
    q=dict(query or {})
    allowed={"aoi_id","scene_id","candidate_id","review_status","observed_from","observed_to"}
    if set(q)-allowed: return {"http_status":400,"body":{"state":"CONTROL_REQUIRED","reason_code":"UNSUPPORTED_QUERY_FILTER","policy_version":POLICY_VERSION}}
    try:
        repo=SQLiteSpatialEvidenceRepository(database_path)
        records=repo.list(aoi_id=q.get("aoi_id"),candidate_id=q.get("candidate_id"))
        if q.get("scene_id") is not None: records=[r for r in records if r.get("scene_id")==q["scene_id"]]
        if q.get("review_status") is not None: records=[r for r in records if r.get("review_status")==q["review_status"]]
        if q.get("observed_from") is not None: records=[r for r in records if r.get("observed_at","")>=q["observed_from"]]
        if q.get("observed_to") is not None: records=[r for r in records if r.get("observed_at","")<=q["observed_to"]]
        records=sorted(records,key=lambda r:(r.get("observed_at",""),r.get("sequence",0),r.get("record_id","")))[:limit]
    except (OSError,ValueError,TypeError,KeyError) as exc:
        return {"http_status":409,"body":{"state":"CONTROL_REQUIRED","reason_code":"PERSISTENT_QUERY_FAILED","error_type":type(exc).__name__,"policy_version":POLICY_VERSION}}
    return {"http_status":200,"body":adapt_query_result(req,{"state":"QUERY_READY","count":len(records),"records":records})}
