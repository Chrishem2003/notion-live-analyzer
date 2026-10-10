import streamlit as st
from nema_agora.api_audit_binding import build_api_audit_event
from nema_agora.api_audit_registry import event_fingerprint
from nema_agora.api_audit_reconciliation import reconcile_api_audit
st.set_page_config(page_title="NEMA-AGORA API Audit Reconciliation",layout="wide")
st.title("NEMA-AGORA — API Audit Reconciliation")
e=build_api_audit_event(request_id="REQ-90-DEMO",actor_id="ACTOR-DEMO",role="coordinator",permission="spatial:evidence:query",authorization_fingerprint="a"*64,query={"aoi_id":"AOI-DEMO"},result={"state":"QUERY_READY","count":0},http_status=200,occurred_at="2026-10-04T12:00:00+00:00")
e["audit_fingerprint"]=event_fingerprint(e)
st.json(reconcile_api_audit([e],["REQ-90-DEMO"]))
st.info("Synthetic reconciliation. CONTROL_REQUIRED means human investigation is required.")
