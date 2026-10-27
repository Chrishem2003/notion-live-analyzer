"""Phase 82 — API-to-repository integration and fail-closed retrieval."""
from __future__ import annotations
from typing import Any,Mapping
from nema_agora.spatial_evidence_store_adapter import EvidenceRepository
from nema_agora.spatial_evidence_service import service_request,adapt_query_result
POLICY_VERSION="phase82-v1"
def retrieve_spatial_evidence(*,repository:EvidenceRepository,request_id:str,query:Mapping[str,Any]|None=None)->dict[str,Any]:
    req=service_request(request_id=request_id,operation="QUERY",query=query)
    if req["state"]!="SERVICE_REQUEST_READY": return {"http_status":400,"body":req}
    q=dict(query or {})
    try:
        records=list(repository.list(
            aoi_id=q.get("aoi_id"),scene_id=q.get("scene_id"),
            candidate_id=q.get("candidate_id"),review_status=q.get("review_status")))
    except Exception as exc:
        return {"http_status":409,"body":{"state":"CONTROL_REQUIRED","reason_code":"REPOSITORY_QUERY_FAILED","error_type":type(exc).__name__,"policy_version":POLICY_VERSION}}
    result={"state":"QUERY_READY","count":len(records),"records":records}
    response=adapt_query_result(req,result)
    return {"http_status":200 if response["state"]=="SERVICE_RESPONSE_READY" else 409,"body":response}
