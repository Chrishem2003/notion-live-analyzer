"""Phase 88 — API audit event binding and request traceability."""
from __future__ import annotations
import hashlib,json
from datetime import datetime,timezone
from typing import Any,Mapping
POLICY_VERSION="phase88-v1"
def fingerprint(value:Any)->str:
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def build_api_audit_event(*,request_id:str,actor_id:str,role:str,permission:str,authorization_fingerprint:str,query:Mapping[str,Any]|None,result:Mapping[str,Any],http_status:int,occurred_at:str|None=None)->dict[str,Any]:
 if not all(isinstance(x,str) and x.strip() for x in (request_id,actor_id,role,permission,authorization_fingerprint)): return {"state":"CONTROL_REQUIRED","reason_code":"INVALID_IDENTITY"}
 if len(authorization_fingerprint)!=64: return {"state":"CONTROL_REQUIRED","reason_code":"INVALID_AUTHORIZATION_FINGERPRINT"}
 try: datetime.fromisoformat((occurred_at or datetime.now(timezone.utc).isoformat()).replace("Z","+00:00"))
 except ValueError: return {"state":"CONTROL_REQUIRED","reason_code":"INVALID_TIMESTAMP"}
 if not isinstance(result,Mapping) or not isinstance(http_status,int) or http_status<100 or http_status>599: return {"state":"CONTROL_REQUIRED","reason_code":"INVALID_RESULT"}
 payload={"request_id":request_id,"actor_id":actor_id,"role":role,"permission":permission,"authorization_fingerprint":authorization_fingerprint,"query_fingerprint":fingerprint(dict(query or {})),"result_fingerprint":fingerprint(dict(result)),"http_status":http_status}
 event=dict(payload,event_id="API-AUDIT-"+fingerprint(payload)[:24],occurred_at=occurred_at or datetime.now(timezone.utc).isoformat(),policy_version=POLICY_VERSION,state="RECORDED",interpretation="API_REQUEST_TRACEABILITY",environmental_conclusion=None,regulatory_conclusion=None,violation=None,enforcement_action=None)
 return event
