import os,tempfile,streamlit as st
from nema_agora.api_audit_binding import build_api_audit_event
from nema_agora.api_audit_registry import ApiAuditRegistry
st.set_page_config(page_title="NEMA-AGORA API Audit Registry",layout="wide")
st.title("NEMA-AGORA — Persistent API Audit Registry")
with tempfile.TemporaryDirectory() as d:
 r=ApiAuditRegistry(os.path.join(d,"audit.db"))
 e=build_api_audit_event(request_id="REQ-89-DEMO",actor_id="ACTOR-DEMO",role="coordinator",permission="spatial:evidence:query",authorization_fingerprint="a"*64,query={"aoi_id":"AOI-DEMO"},result={"state":"QUERY_READY","count":0},http_status=200,occurred_at="2026-10-04T12:00:00+00:00")
 st.json(r.append(e)); st.json(r.list())
st.info("Synthetic persistent audit demonstration. Registry is append-only and evidence-only.")
