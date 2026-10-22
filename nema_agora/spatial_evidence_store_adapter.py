"""Phase 80 — spatial evidence API integration and persistent store adapter."""
from __future__ import annotations
from typing import Any,Mapping,Protocol,Sequence
from nema_agora.spatial_evidence_service import service_request,adapt_query_result
POLICY_VERSION="phase80-v1"
class EvidenceRepository(Protocol):
 def list(self,**filters:Any)->Sequence[Mapping[str,Any]]: ...
class InMemoryEvidenceRepository:
 def __init__(self,records:Sequence[Mapping[str,Any]]=()): self._records=[dict(x) for x in records]
 def list(self,**filters:Any)->list[dict[str,Any]]:
  return [r for r in self._records if all(v is None or r.get(k)==v for k,v in filters.items())]
def execute_query(*,repository:EvidenceRepository,request_id:str,operation:str="QUERY",query:Mapping[str,Any]|None=None)->dict[str,Any]:
 req=service_request(request_id=request_id,operation=operation,query=query)
 if req["state"]!="SERVICE_REQUEST_READY": return {"http_status":400,"body":req}
 q=dict(query or {})
 records=repository.list(aoi_id=q.get("aoi_id"),scene_id=q.get("scene_id"),candidate_id=q.get("candidate_id"),review_status=q.get("review_status"))
 result={"state":"QUERY_READY","count":len(records),"records":[dict(r) for r in records]}
 response=adapt_query_result(req,result)
 return {"http_status":200 if response["state"]=="SERVICE_RESPONSE_READY" else 409,"body":response}
