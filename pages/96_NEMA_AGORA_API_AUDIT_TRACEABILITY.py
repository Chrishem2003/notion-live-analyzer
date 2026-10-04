import streamlit as st
from nema_agora.api_audit_binding import build_api_audit_event
st.set_page_config(page_title="NEMA-AGORA API Audit Traceability",layout="wide")
st.title("NEMA-AGORA — API Audit Traceability")
event=build_api_audit_event(request_id="REQ-88-DEMO",actor_id="ACTOR-DEMO",role="coordinator",permission="spatial:evidence:query",authorization_fingerprint="a"*64,query={"aoi_id":"AOI-DEMO"},result={"state":"QUERY_READY","count":0},http_status=200,occurred_at="2026-10-04T12:00:00+00:00")
st.json(event)
st.info("Synthetic, deterministic audit evidence. No environmental or regulatory conclusion is generated.")
