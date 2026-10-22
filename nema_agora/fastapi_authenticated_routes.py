"""Phase 87 — authenticated FastAPI route wiring."""
from __future__ import annotations
from typing import Any
from nema_agora.authenticated_spatial_api import authenticated_query
POLICY_VERSION="phase87-v1"
try:
 from fastapi import FastAPI,HTTPException,Header
 app=FastAPI(title="NEMA-AGORA Authenticated Spatial Evidence API",version=POLICY_VERSION)
 FASTAPI_AVAILABLE=True
 @app.get("/api/v1/spatial-evidence/health")
 def health()->dict[str,str]: return {"status":"ok","policy_version":POLICY_VERSION,"read_only":"true"}
 @app.get("/api/v1/spatial-evidence/query")
 def query(request_id:str,database_path:str,actor_id:str,role:str,aoi_id:str|None=None,scene_id:str|None=None,candidate_id:str|None=None,review_status:str|None=None,observed_from:str|None=None,observed_to:str|None=None,limit:int=100,authorization:str|None=Header(default=None))->dict[str,Any]:
  result=authenticated_query(database_path=database_path,actor_id=actor_id,role=role,request_id=request_id,query={k:v for k,v in {"aoi_id":aoi_id,"scene_id":scene_id,"candidate_id":candidate_id,"review_status":review_status,"observed_from":observed_from,"observed_to":observed_to}.items() if v is not None},limit=limit,token_present=bool(authorization))
  if result["http_status"]>=400: raise HTTPException(result["http_status"],detail=result["body"])
  return result["body"]
except ImportError:
 app=None;FASTAPI_AVAILABLE=False
