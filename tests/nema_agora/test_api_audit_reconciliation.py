from nema_agora.api_audit_binding import build_api_audit_event
from nema_agora.api_audit_registry import event_fingerprint
from nema_agora.api_audit_reconciliation import reconcile_api_audit
def ev():
 return build_api_audit_event(request_id="REQ-90",actor_id="ACTOR-1",role="coordinator",permission="spatial:evidence:query",authorization_fingerprint="a"*64,query={},result={"state":"QUERY_READY"},http_status=200,occurred_at="2026-10-04T12:00:00+00:00")
def test_reconciled():
 e=ev();e["audit_fingerprint"]=event_fingerprint(e)
 r=reconcile_api_audit([e],["REQ-90"])
 assert r["state"]=="RECONCILED" and r["finding_count"]==0
def test_missing_request_control():
 e=ev();e["audit_fingerprint"]=event_fingerprint(e)
 r=reconcile_api_audit([e],["REQ-90","REQ-MISSING"])
 assert r["state"]=="CONTROL_REQUIRED" and any(x["code"]=="MISSING_REQUEST_AUDIT" for x in r["findings"])
def test_tamper_detected():
 e=ev();e["audit_fingerprint"]=event_fingerprint(e);e["role"]="admin"
 r=reconcile_api_audit([e],["REQ-90"])
 assert r["state"]=="CONTROL_REQUIRED"
