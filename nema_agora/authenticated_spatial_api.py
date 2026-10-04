"""Phase 86 — authenticated FastAPI query integration."""
from __future__ import annotations
from typing import Any,Mapping
from nema_agora.spatial_api_auth import authorize_request
from nema_agora.spatial_evidence_api_hardening import query_persistent_evidence
POLICY_VERSION="phase86-v1"
def authenticated_query(*,database_path:str,actor_id:str,role:str,request_id:str,query:Mapping[str,Any]|None=None,limit:int=100,token_present:bool=True)->dict[str,Any]:
    auth=authorize_request(actor_id=actor_id,role=role,permission="spatial:evidence:query",request_id=request_id,token_present=token_present)
    if auth["state"]!="AUTHORIZED": return {"http_status":auth["http_status"],"body":auth}
    result=query_persistent_evidence(database_path=database_path,request_id=request_id,query=query,limit=limit)
    if result["http_status"]>=400: return result
    body=dict(result["body"])
    body["authorization_context"]=auth["context"]
    body["authorization_fingerprint"]=auth["authorization_fingerprint"]
    body["policy_version"]=POLICY_VERSION
    return {"http_status":200,"body":body}
