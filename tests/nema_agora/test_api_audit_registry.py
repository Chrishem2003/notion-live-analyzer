import tempfile,os
from nema_agora.api_audit_binding import build_api_audit_event
from nema_agora.api_audit_registry import ApiAuditRegistry
def event():
 return build_api_audit_event(request_id="REQ-89",actor_id="ACTOR-1",role="coordinator",permission="spatial:evidence:query",authorization_fingerprint="a"*64,query={"aoi_id":"AOI-1"},result={"state":"QUERY_READY"},http_status=200,occurred_at="2026-10-04T12:00:00+00:00")
def test_append_and_query():
 with tempfile.TemporaryDirectory() as d:
  r=ApiAuditRegistry(os.path.join(d,"audit.db")); e=r.append(event())
  assert len(r.list("REQ-89"))==1 and len(e["audit_fingerprint"])==64
def test_duplicate_rejected():
 with tempfile.TemporaryDirectory() as d:
  r=ApiAuditRegistry(os.path.join(d,"audit.db")); e=event(); r.append(e)
  try:r.append(e);assert False
  except ValueError as x: assert str(x)=="API_AUDIT_EVENT_CONFLICT"
def test_update_delete_blocked():
 with tempfile.TemporaryDirectory() as d:
  r=ApiAuditRegistry(os.path.join(d,"audit.db")); r.append(event())
  import sqlite3
  with sqlite3.connect(r.database_path) as c:
   for sql in ("UPDATE api_audit_events SET role='admin'","DELETE FROM api_audit_events"):
    try:c.execute(sql);assert False
    except sqlite3.DatabaseError as x: assert "append-only" in str(x)
