"""Phase 85 — authentication and authorization boundary for spatial evidence API."""
from __future__ import annotations
import hashlib,json,re
from typing import Any,Mapping
POLICY_VERSION="phase85-v1"
_ID=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
ROLES={"reviewer":{"spatial:evidence:read"},"coordinator":{"spatial:evidence:read","spatial:evidence:query"},"admin":{"spatial:evidence:read","spatial:evidence:query","spatial:evidence:admin"}}
def fingerprint(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def authorize_request(*,actor_id:str,role:str,permission:str,request_id:str,token_present:bool=True)->dict[str,Any]:
    if not token_present:return {"state":"CONTROL_REQUIRED","reason_code":"AUTHENTICATION_REQUIRED","http_status":401,"policy_version":POLICY_VERSION}
    if not _ID.fullmatch(actor_id or "") or role not in ROLES or permission not in ROLES[role] or not _ID.fullmatch(request_id or ""):
        return {"state":"CONTROL_REQUIRED","reason_code":"AUTHORIZATION_DENIED","http_status":403,"policy_version":POLICY_VERSION}
    context={"actor_id":actor_id,"role":role,"permission":permission,"request_id":request_id,"policy_version":POLICY_VERSION}
    return {"state":"AUTHORIZED","http_status":200,"authorization_fingerprint":fingerprint(context),"context":context,"read_only":True,"environmental_conclusion":None,"regulatory_conclusion":None}
