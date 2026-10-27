"""Phase 84 — FastAPI application wiring for spatial evidence."""
from __future__ import annotations
from typing import Any
from pathlib import Path
from nema_agora.spatial_evidence_api_hardening import query_persistent_evidence
POLICY_VERSION="phase84-v1"
try:
    from fastapi import FastAPI,HTTPException,Query
    app=FastAPI(title="NEMA-AGORA Spatial Evidence API",version=POLICY_VERSION)
    FASTAPI_AVAILABLE=True
    @app.get("/api/v1/spatial-evidence/health")
    def health()->dict[str,str]:
        return {"status":"ok","policy_version":POLICY_VERSION,"read_only":"true"}
    @app.get("/api/v1/spatial-evidence/query")
    def query(request_id:str, database_path:str=Query(...), aoi_id:str|None=None, scene_id:str|None=None, candidate_id:str|None=None, review_status:str|None=None, observed_from:str|None=None, observed_to:str|None=None, limit:int=100)->dict[str,Any]:
        result=query_persistent_evidence(database_path=database_path,request_id=request_id,query={k:v for k,v in {"aoi_id":aoi_id,"scene_id":scene_id,"candidate_id":candidate_id,"review_status":review_status,"observed_from":observed_from,"observed_to":observed_to}.items() if v is not None},limit=limit)
        if result["http_status"]>=400: raise HTTPException(result["http_status"],detail=result["body"])
        return result["body"]
except ImportError:
    app=None
    FASTAPI_AVAILABLE=False
def app_contract()->dict[str,Any]:
    return {"application":"NEMA-AGORA Spatial Evidence API","policy_version":POLICY_VERSION,"fastapi_available":FASTAPI_AVAILABLE,"read_only":True,"authorization_required":True,"environmental_conclusion":None,"regulatory_conclusion":None}
