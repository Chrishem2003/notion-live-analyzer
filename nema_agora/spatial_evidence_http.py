"""Phase 79 — FastAPI-ready spatial evidence HTTP contract."""
from __future__ import annotations
from typing import Any,Mapping
from nema_agora.spatial_evidence_service import service_request,adapt_query_result
POLICY_VERSION="phase79-v1"
try:
 from fastapi import APIRouter,HTTPException
 router=APIRouter(prefix="/api/v1/spatial-evidence",tags=["spatial-evidence"])
 FASTAPI_AVAILABLE=True
except ImportError:
 router=None;FASTAPI_AVAILABLE=False
def handle_request(*,request_id:str,operation:str,query:Mapping[str,Any]|None=None,result:Mapping[str,Any]|None=None)->dict[str,Any]:
 req=service_request(request_id=request_id,operation=operation,query=query)
 if req["state"]!="SERVICE_REQUEST_READY": return {"http_status":400,"body":req}
 if result is None: return {"http_status":202,"body":req}
 response=adapt_query_result(req,result)
 return {"http_status":200 if response["state"]=="SERVICE_RESPONSE_READY" else 409,"body":response}
if FASTAPI_AVAILABLE:
 @router.get("/health")
 def health()->dict[str,str]: return {"status":"ok","policy_version":POLICY_VERSION,"read_only":"true"}
 @router.post("/query")
 def query(request_id:str,operation:str="QUERY",aoi_id:str|None=None)->dict[str,Any]:
  response=handle_request(request_id=request_id,operation=operation,query={"aoi_id":aoi_id} if aoi_id else {})
  if response["http_status"]>=400: raise HTTPException(response["http_status"],detail=response["body"])
  return response["body"]
