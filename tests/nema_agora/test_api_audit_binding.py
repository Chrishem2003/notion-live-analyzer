from nema_agora.api_audit_binding import build_api_audit_event
def test_builds_deterministic_audit_event():
 a={"state":"QUERY_READY","count":0}
 x=build_api_audit_event(request_id="REQ-88",actor_id="ACTOR-1",role="coordinator",permission="spatial:evidence:query",authorization_fingerprint="a"*64,query={"aoi_id":"AOI-1"},result=a,http_status=200,occurred_at="2026-10-04T12:00:00+00:00")
 y=build_api_audit_event(request_id="REQ-88",actor_id="ACTOR-1",role="coordinator",permission="spatial:evidence:query",authorization_fingerprint="a"*64,query={"aoi_id":"AOI-1"},result=a,http_status=200,occurred_at="2026-10-04T12:00:00+00:00")
 assert x["state"]=="RECORDED" and x["event_id"]==y["event_id"] and x["query_fingerprint"] and x["result_fingerprint"]
def test_invalid_auth_fails_closed():
 x=build_api_audit_event(request_id="REQ-88",actor_id="ACTOR-1",role="coordinator",permission="spatial:evidence:query",authorization_fingerprint="bad",query={},result={},http_status=200)
 assert x["state"]=="CONTROL_REQUIRED"
